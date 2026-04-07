"""Local daemon PID helpers."""

from __future__ import annotations

import os
import sys
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
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    if _is_zombie_process(pid):
        return False
    return True


def _is_zombie_process(pid: int) -> bool:
    if not sys.platform.startswith("linux"):
        return False

    stat_path = Path(f"/proc/{pid}/stat")
    try:
        stat_content = stat_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    except OSError:
        return False

    closing_paren = stat_content.rfind(")")
    if closing_paren == -1:
        return False

    trailing_fields = stat_content[closing_paren + 2 :].split()
    if not trailing_fields:
        return False
    return trailing_fields[0] == "Z"
