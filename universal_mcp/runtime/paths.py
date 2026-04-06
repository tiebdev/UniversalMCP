"""Filesystem paths for local runtime state."""

from __future__ import annotations

from pathlib import Path


def runtime_dir(root: Path | None = None) -> Path:
    base = root or Path.cwd()
    return base / ".universal_mcp_runtime"


def pid_file(root: Path | None = None) -> Path:
    return runtime_dir(root) / "daemon.pid"


def state_file(root: Path | None = None) -> Path:
    return runtime_dir(root) / "daemon-state.json"


def log_file(root: Path | None = None) -> Path:
    return runtime_dir(root) / "daemon.log"


def events_file(root: Path | None = None) -> Path:
    return runtime_dir(root) / "events.jsonl"
