from pathlib import Path

from universal_mcp.config.settings import save_settings
from universal_mcp.config.settings import Settings
from universal_mcp.daemon.process_router import ProcessRouter
from universal_mcp.runtime import daemon_control
from universal_mcp.runtime.pid import read_pid, write_pid
from universal_mcp.runtime.state_store import read_state, write_state
from universal_mcp.daemon.state import DaemonStatus


class _FakeProcess:
    def __init__(self, *, pid: int = 4321, poll_values: list[int | None] | None = None) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self._poll_values = poll_values or [None]

    def poll(self) -> int | None:
        value = self._poll_values.pop(0) if self._poll_values else self.returncode
        self.returncode = value
        return value


def test_start_daemon_reports_port_conflict_from_log(monkeypatch, tmp_path: Path) -> None:
    settings = Settings()
    logfile = daemon_control.log_file(tmp_path)
    logfile.parent.mkdir(parents=True, exist_ok=True)
    logfile.write_text("ERROR: could not bind on any address out of [('127.0.0.1', 8765)]\n", encoding="utf-8")

    monkeypatch.setattr(daemon_control, "read_pid", lambda root=None: None)
    monkeypatch.setattr(daemon_control, "is_process_running", lambda pid: False)
    monkeypatch.setattr(daemon_control, "daemon_is_responsive", lambda port, timeout=0.5: False)
    monkeypatch.setattr(daemon_control, "local_listener_preflight", lambda: (True, "Listeners locales disponibles"))
    monkeypatch.setattr(daemon_control, "port_is_in_use", lambda port, timeout=0.5: False)
    monkeypatch.setattr(daemon_control.subprocess, "Popen", lambda *args, **kwargs: _FakeProcess(poll_values=[1]))
    monkeypatch.setattr(daemon_control.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(daemon_control, "suggest_free_ports", lambda start_port, count=3: [8766, 8767, 8768])

    started, message = daemon_control.start_daemon(settings, root=tmp_path)

    assert started is False
    assert "puerto 8765 ya está ocupado" in message
    assert "8766, 8767, 8768" in message
    assert str(logfile) in message


def test_start_daemon_reports_last_log_excerpt_on_generic_boot_failure(monkeypatch, tmp_path: Path) -> None:
    settings = Settings()
    logfile = daemon_control.log_file(tmp_path)
    logfile.parent.mkdir(parents=True, exist_ok=True)
    logfile.write_text("Traceback\nRuntimeError: boom\n", encoding="utf-8")

    monkeypatch.setattr(daemon_control, "read_pid", lambda root=None: None)
    monkeypatch.setattr(daemon_control, "is_process_running", lambda pid: False)
    monkeypatch.setattr(daemon_control, "daemon_is_responsive", lambda port, timeout=0.5: False)
    monkeypatch.setattr(daemon_control, "local_listener_preflight", lambda: (True, "Listeners locales disponibles"))
    monkeypatch.setattr(daemon_control, "port_is_in_use", lambda port, timeout=0.5: False)
    monkeypatch.setattr(daemon_control.subprocess, "Popen", lambda *args, **kwargs: _FakeProcess(poll_values=[2]))
    monkeypatch.setattr(daemon_control.time, "sleep", lambda *_args, **_kwargs: None)

    started, message = daemon_control.start_daemon(settings, root=tmp_path)

    assert started is False
    assert "El daemon no respondió tras arrancar" in message
    assert "RuntimeError: boom" in message


def test_suggest_free_ports_skips_ports_in_use(monkeypatch) -> None:
    monkeypatch.setattr(daemon_control, "port_is_in_use", lambda port, timeout=0.5: port in {8766, 8768})

    suggestions = daemon_control.suggest_free_ports(start_port=8765, count=3)

    assert suggestions == [8767, 8769, 8770]


def test_local_listener_preflight_reports_permission_restriction(monkeypatch) -> None:
    def _forbidden_socket(*_args, **_kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(daemon_control.socket, "socket", _forbidden_socket)

    ok, message = daemon_control.local_listener_preflight()

    assert ok is False
    assert "bloquea la creacion de listeners locales" in message
    assert "PermissionError" in message


def test_start_daemon_reports_environment_listener_restriction(monkeypatch, tmp_path: Path) -> None:
    settings = Settings()

    monkeypatch.setattr(daemon_control, "read_pid", lambda root=None: None)
    monkeypatch.setattr(daemon_control, "is_process_running", lambda pid: False)
    monkeypatch.setattr(daemon_control, "daemon_is_responsive", lambda port, timeout=0.5: False)
    monkeypatch.setattr(
        daemon_control,
        "local_listener_preflight",
        lambda: (False, "Este entorno bloquea la creacion de listeners locales"),
    )

    started, message = daemon_control.start_daemon(settings, root=tmp_path)

    assert started is False
    assert "bloquea la creacion de listeners locales" in message


def test_stop_daemon_succeeds_when_process_exits_even_if_port_check_lags(monkeypatch, tmp_path: Path) -> None:
    write_pid(4321, root=tmp_path)
    write_state(DaemonStatus(port=8765, default_profile="work"), root=tmp_path)

    running_states = iter([True, False])
    monkeypatch.setattr(daemon_control, "read_pid", lambda root=None: 4321)
    monkeypatch.setattr(daemon_control, "is_process_running", lambda pid: next(running_states, False))
    monkeypatch.setattr(daemon_control, "daemon_is_responsive", lambda port, timeout=0.5: True)
    monkeypatch.setattr(daemon_control.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(daemon_control.time, "sleep", lambda *_args, **_kwargs: None)

    stopped, message = daemon_control.stop_daemon(8765, root=tmp_path)

    assert stopped is True
    assert "Daemon detenido (PID 4321)" in message
    assert read_pid(tmp_path) is None
    assert read_state(tmp_path) is None


def test_stop_daemon_escalates_to_sigkill_when_sigterm_is_not_enough(monkeypatch, tmp_path: Path) -> None:
    write_pid(7777, root=tmp_path)
    write_state(DaemonStatus(port=8765, default_profile="work"), root=tmp_path)

    kill_signals: list[int] = []
    running_states = iter([True] * 42 + [False])

    monkeypatch.setattr(daemon_control, "read_pid", lambda root=None: 7777)
    monkeypatch.setattr(daemon_control, "is_process_running", lambda pid: next(running_states, False))
    monkeypatch.setattr(daemon_control, "daemon_is_responsive", lambda port, timeout=0.5: False)
    monkeypatch.setattr(daemon_control.os, "kill", lambda pid, sig: kill_signals.append(sig))
    monkeypatch.setattr(daemon_control.time, "sleep", lambda *_args, **_kwargs: None)

    stopped, message = daemon_control.stop_daemon(8765, root=tmp_path)

    assert stopped is True
    assert kill_signals == [daemon_control.signal.SIGTERM, daemon_control.signal.SIGKILL]
    assert "SIGKILL" in message
    assert read_pid(tmp_path) is None
    assert read_state(tmp_path) is None


def test_describe_daemon_clears_stale_pid_and_state(monkeypatch, tmp_path: Path) -> None:
    settings = Settings()
    write_pid(9999, root=tmp_path)
    write_state(DaemonStatus(port=8765, default_profile="work"), root=tmp_path)

    monkeypatch.setattr(daemon_control, "read_pid", lambda root=None: 9999)
    monkeypatch.setattr(daemon_control, "is_process_running", lambda pid: False)
    monkeypatch.setattr(daemon_control, "daemon_is_responsive", lambda port, timeout=0.5: False)

    is_running, message, pid = daemon_control.describe_daemon(settings, root=tmp_path)

    assert is_running is False
    assert message == "Daemon detenido"
    assert pid is None
    assert read_pid(tmp_path) is None
    assert read_state(tmp_path) is None


def test_probe_daemon_app_validates_asgi_app_without_starting_processes(monkeypatch, tmp_path: Path) -> None:
    settings = Settings()
    save_settings(tmp_path / ".universal_mcp.json", settings)

    async def _unexpected_start_all(self) -> None:
        raise AssertionError("start_all should not be called during ASGI probe")

    monkeypatch.setattr(ProcessRouter, "start_all", _unexpected_start_all)

    ok, message = daemon_control.probe_daemon_app(settings, root=tmp_path)

    assert ok is True
    assert "sin bind real" in message
    assert "/healthz ok" in message
    assert "/status ok" in message
