"""Daemon process lifecycle helpers for the CLI."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from universal_mcp.config.settings import Settings
from universal_mcp.runtime.paths import log_file, runtime_dir
from universal_mcp.runtime.pid import clear_pid, is_process_running, read_pid
from universal_mcp.runtime.state_store import read_state


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


def start_daemon(settings: Settings, root: Path | None = None) -> tuple[bool, str]:
    pid = read_pid(root)
    if pid and is_process_running(pid) and daemon_is_responsive(settings.runtime.port):
        return False, f"Daemon ya operativo con PID {pid}"
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
        return False, "El PID registrado no corresponde a un proceso activo"

    os.kill(pid, signal.SIGTERM)

    for _ in range(40):
        if not is_process_running(pid) and not daemon_is_responsive(port):
            clear_pid(root)
            return True, f"Daemon detenido (PID {pid})"
        time.sleep(0.25)

    return False, f"No se pudo confirmar el apagado del daemon PID {pid}"


def describe_daemon(settings: Settings, root: Path | None = None) -> tuple[bool, str, int | None]:
    pid = read_pid(root)
    responsive = daemon_is_responsive(settings.runtime.port)
    if pid and is_process_running(pid) and responsive:
        return True, "Daemon activo", pid
    if pid and not is_process_running(pid):
        return False, "PID huérfano detectado", pid
    if responsive:
        return False, "Puerto activo sin PID reconocido", pid
    return False, "Daemon detenido", pid


def last_known_status(root: Path | None = None):
    return read_state(root)


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
