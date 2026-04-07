"""Daemon process lifecycle helpers for the CLI."""

from __future__ import annotations

import asyncio
import errno
import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI

from universal_mcp.config.settings import Settings
from universal_mcp.daemon.server import create_daemon_app
from universal_mcp.runtime.paths import log_file, runtime_dir
from universal_mcp.runtime.pid import clear_pid, is_process_running, read_pid
from universal_mcp.runtime.state_store import clear_state, read_state


def daemon_is_responsive(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            pass
        with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=timeout) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def port_is_in_use(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def suggest_free_ports(*, start_port: int, count: int = 3) -> list[int]:
    suggestions: list[int] = []
    candidate = start_port + 1
    while len(suggestions) < count and candidate <= 65535:
        if not port_is_in_use(candidate):
            suggestions.append(candidate)
        candidate += 1
    return suggestions


def local_listener_preflight() -> tuple[bool, str]:
    sock: socket.socket | None = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
    except PermissionError as exc:
        return False, (
            "Este entorno bloquea la creacion de listeners locales "
            f"({exc.__class__.__name__}: {exc})."
        )
    except OSError as exc:
        if exc.errno in {errno.EPERM, errno.EACCES}:
            return False, (
                "Este entorno bloquea la creacion de listeners locales "
                f"({exc.__class__.__name__}: {exc})."
            )
        return False, f"Fallo al validar listeners locales: {exc.__class__.__name__}: {exc}"
    finally:
        if sock is not None:
            sock.close()
    return True, "Listeners locales disponibles"


def start_daemon(settings: Settings, root: Path | None = None) -> tuple[bool, str]:
    pid = read_pid(root)
    if pid and is_process_running(pid) and daemon_is_responsive(settings.runtime.port):
        return False, f"Daemon ya operativo con PID {pid}"
    listeners_ok, listeners_message = local_listener_preflight()
    if not listeners_ok:
        return False, listeners_message
    if port_is_in_use(settings.runtime.port) and not daemon_is_responsive(settings.runtime.port):
        return False, _port_in_use_message(settings.runtime.port)

    directory = runtime_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    logfile = log_file(root)
    with logfile.open("ab") as stream:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "universal_mcp.daemon.server",
                "--port",
                str(settings.runtime.port),
                "--default-profile",
                settings.default_profile,
                "--root",
                str(root or Path.cwd()),
            ],
            stdout=stream,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    for _ in range(40):
        if daemon_is_responsive(settings.runtime.port):
            return True, f"Daemon arrancado con PID {process.pid}"
        if process.poll() is not None:
            return False, _startup_failure_message(
                port=settings.runtime.port,
                logfile=logfile,
                process_exit_code=process.returncode,
            )
        time.sleep(0.25)

    return False, _startup_failure_message(
        port=settings.runtime.port,
        logfile=logfile,
        process_exit_code=process.poll(),
    )


def stop_daemon(port: int, root: Path | None = None) -> tuple[bool, str]:
    pid = read_pid(root)
    if not pid:
        return False, "No hay PID registrado para el daemon"

    if not is_process_running(pid):
        clear_pid(root)
        clear_state(root)
        return False, "El PID registrado no corresponde a un proceso activo"

    os.kill(pid, signal.SIGTERM)

    if _wait_for_pid_exit(pid, attempts=40, delay_seconds=0.25):
        return _finalize_stop_success(pid=pid, port=port, root=root)

    os.kill(pid, signal.SIGKILL)

    if _wait_for_pid_exit(pid, attempts=20, delay_seconds=0.25):
        stopped, message = _finalize_stop_success(pid=pid, port=port, root=root)
        if stopped:
            return True, f"{message} tras SIGKILL"
        return stopped, message

    return False, f"No se pudo confirmar el apagado del daemon PID {pid}"


def describe_daemon(settings: Settings, root: Path | None = None) -> tuple[bool, str, int | None]:
    pid = read_pid(root)
    responsive = daemon_is_responsive(settings.runtime.port)
    if pid and is_process_running(pid) and responsive:
        return True, "Daemon activo", pid
    if pid and not is_process_running(pid):
        clear_pid(root)
        clear_state(root)
        if responsive:
            return False, "Puerto activo sin PID reconocido", None
        return False, "Daemon detenido", None
    if responsive:
        return False, "Puerto activo sin PID reconocido", pid
    return False, "Daemon detenido", pid


def last_known_status(root: Path | None = None):
    return read_state(root)


def probe_daemon_app(settings: Settings, root: Path | None = None) -> tuple[bool, str]:
    root_path = (root or Path.cwd()).resolve()

    try:
        app = create_daemon_app(
            default_profile=settings.default_profile,
            port=settings.runtime.port,
            root=root_path,
            start_router_processes=False,
        )
    except Exception as exc:
        return False, f"No se pudo construir el app del daemon: {exc}"

    try:
        health_payload, status_payload = asyncio.run(_run_app_probe(app))
    except Exception as exc:
        return False, f"La validacion sin bind real del daemon fallo: {exc}"

    if health_payload.get("status") != "ok":
        return False, "La respuesta de /healthz no contiene status=ok"

    payload = status_payload
    if payload.get("default_profile") != settings.default_profile:
        return False, "La respuesta de /status no refleja el perfil por defecto configurado"
    if payload.get("port") != settings.runtime.port:
        return False, "La respuesta de /status no refleja el puerto runtime configurado"

    processes = payload.get("processes", [])
    return (
        True,
        "App del daemon validada sin bind real: "
        f"/healthz ok, /status ok, {len(processes)} MCPs visibles",
    )


async def _run_app_probe(app: FastAPI) -> tuple[dict[str, str], dict[str, Any]]:
    async with app.router.lifespan_context(app):
        health_handler = _route_endpoint(app, "/healthz", "GET")
        status_handler = _route_endpoint(app, "/status", "GET")
        health_payload = await health_handler()
        status_payload = await status_handler()
    return health_payload, status_payload.model_dump(mode="json")


def _route_endpoint(app: FastAPI, path: str, method: str) -> Callable[[], Awaitable[Any]]:
    for route in app.routes:
        route_path = getattr(route, "path", None)
        route_methods = getattr(route, "methods", set())
        endpoint = getattr(route, "endpoint", None)
        if route_path == path and method in route_methods and endpoint is not None:
            return endpoint
    raise RuntimeError(f"No se encontro la ruta {method} {path} en el app del daemon")


def _startup_failure_message(*, port: int, logfile: Path, process_exit_code: int | None) -> str:
    log_excerpt = _read_log_excerpt(logfile)
    lowered_excerpt = log_excerpt.lower()

    if "could not bind on any address" in lowered_excerpt or "address already in use" in lowered_excerpt:
        return f"{_port_in_use_message(port)} Revisa {logfile}"

    if log_excerpt:
        suffix = f" Último error: {log_excerpt}"
    elif process_exit_code is not None:
        suffix = f" El proceso terminó con código {process_exit_code}."
    else:
        suffix = ""

    return f"El daemon no respondió tras arrancar. Revisa {logfile}.{suffix}"


def _read_log_excerpt(logfile: Path, max_lines: int = 3) -> str:
    if not logfile.exists():
        return ""
    lines = [line.strip() for line in logfile.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    if not lines:
        return ""
    return " | ".join(lines[-max_lines:])


def _port_in_use_message(port: int) -> str:
    suggestions = suggest_free_ports(start_port=port)
    if suggestions:
        suggested = ", ".join(str(item) for item in suggestions)
        return (
            f"El puerto {port} ya está ocupado por otro proceso. "
            f"Puertos libres sugeridos: {suggested}"
        )
    return f"El puerto {port} ya está ocupado por otro proceso."


def _wait_for_pid_exit(pid: int, *, attempts: int, delay_seconds: float) -> bool:
    for _ in range(attempts):
        if not is_process_running(pid):
            return True
        time.sleep(delay_seconds)
    return not is_process_running(pid)


def _finalize_stop_success(*, pid: int, port: int, root: Path | None) -> tuple[bool, str]:
    clear_pid(root)
    clear_state(root)
    if daemon_is_responsive(port):
        return True, f"Daemon detenido (PID {pid}), pero el puerto {port} sigue respondiendo"
    return True, f"Daemon detenido (PID {pid})"
