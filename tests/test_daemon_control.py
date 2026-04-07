from pathlib import Path

from universal_mcp.config.settings import Settings
from universal_mcp.runtime import daemon_control


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
    monkeypatch.setattr(daemon_control, "port_is_in_use", lambda port, timeout=0.5: False)
    monkeypatch.setattr(daemon_control.subprocess, "Popen", lambda *args, **kwargs: _FakeProcess(poll_values=[1]))
    monkeypatch.setattr(daemon_control.time, "sleep", lambda *_args, **_kwargs: None)

    started, message = daemon_control.start_daemon(settings, root=tmp_path)

    assert started is False
    assert "puerto 8765 ya está en uso" in message
    assert str(logfile) in message


def test_start_daemon_reports_last_log_excerpt_on_generic_boot_failure(monkeypatch, tmp_path: Path) -> None:
    settings = Settings()
    logfile = daemon_control.log_file(tmp_path)
    logfile.parent.mkdir(parents=True, exist_ok=True)
    logfile.write_text("Traceback\nRuntimeError: boom\n", encoding="utf-8")

    monkeypatch.setattr(daemon_control, "read_pid", lambda root=None: None)
    monkeypatch.setattr(daemon_control, "is_process_running", lambda pid: False)
    monkeypatch.setattr(daemon_control, "daemon_is_responsive", lambda port, timeout=0.5: False)
    monkeypatch.setattr(daemon_control, "port_is_in_use", lambda port, timeout=0.5: False)
    monkeypatch.setattr(daemon_control.subprocess, "Popen", lambda *args, **kwargs: _FakeProcess(poll_values=[2]))
    monkeypatch.setattr(daemon_control.time, "sleep", lambda *_args, **_kwargs: None)

    started, message = daemon_control.start_daemon(settings, root=tmp_path)

    assert started is False
    assert "El daemon no respondió tras arrancar" in message
    assert "RuntimeError: boom" in message
