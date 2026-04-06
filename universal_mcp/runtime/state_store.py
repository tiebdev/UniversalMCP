"""Helpers to persist daemon state locally."""

from __future__ import annotations

import json
from pathlib import Path

from universal_mcp.daemon.state import DaemonStatus
from universal_mcp.runtime.paths import runtime_dir, state_file


def write_state(status: DaemonStatus, root: Path | None = None) -> Path:
    directory = runtime_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = state_file(root)
    path.write_text(json.dumps(status.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path


def read_state(root: Path | None = None) -> DaemonStatus | None:
    path = state_file(root)
    if not path.exists():
        return None
    return DaemonStatus.model_validate_json(path.read_text(encoding="utf-8"))


def clear_state(root: Path | None = None) -> None:
    path = state_file(root)
    if path.exists():
        path.unlink()
