"""Local daemon PID helpers."""

from __future__ import annotations

import os
from pathlib import Path

from universal_mcp.runtime.paths import pid_file, runtime_dir


def write_pid(pid: int, root: Path | None = None) -> Path:
    directory = runtime_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = pid_file(root)
    path.write_text(str(pid), encoding="utf-8")
    return path


def read_pid(root: Path | None = None) -> int | None:
    path = pid_file(root)
    if not path.exists():
        return None
    return int(path.read_text(encoding="utf-8").strip())


def clear_pid(root: Path | None = None) -> None:
    path = pid_file(root)
    if path.exists():
        path.unlink()


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
