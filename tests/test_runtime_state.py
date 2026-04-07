from pathlib import Path

from universal_mcp.config.settings import Settings, load_settings, save_settings
from universal_mcp.runtime import pid as pid_module
from universal_mcp.runtime.pid import clear_pid, is_process_running, read_pid, write_pid
from universal_mcp.runtime.state_store import clear_state, read_state, write_state
from universal_mcp.daemon.state import DaemonStatus


def test_settings_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(default_profile="personal")
    save_settings(path, settings)
    loaded = load_settings(path)
    assert loaded.default_profile == "personal"


def test_pid_roundtrip(tmp_path: Path) -> None:
    path_root = tmp_path
    write_pid(12345, root=path_root)
    assert read_pid(path_root) == 12345
    clear_pid(path_root)
    assert read_pid(path_root) is None


def test_clear_pid_is_idempotent(tmp_path: Path) -> None:
    clear_pid(tmp_path)
    write_pid(12345, root=tmp_path)
    clear_pid(tmp_path)
    clear_pid(tmp_path)
    assert read_pid(tmp_path) is None


def test_process_running_for_current_pid() -> None:
    assert is_process_running(1) or is_process_running(__import__("os").getpid())


def test_is_process_running_treats_linux_zombie_as_not_running(monkeypatch) -> None:
    monkeypatch.setattr(pid_module.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(pid_module, "_is_zombie_process", lambda pid: True)

    assert is_process_running(12345) is False


def test_is_process_running_keeps_non_zombie_process_as_running(monkeypatch) -> None:
    monkeypatch.setattr(pid_module.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(pid_module, "_is_zombie_process", lambda pid: False)

    assert is_process_running(12345) is True


def test_state_roundtrip(tmp_path: Path) -> None:
    status = DaemonStatus(port=8765, default_profile="work")
    write_state(status, root=tmp_path)
    loaded = read_state(tmp_path)
    assert loaded is not None
    assert loaded.port == 8765
    assert loaded.default_profile == "work"
    clear_state(tmp_path)
    assert read_state(tmp_path) is None
