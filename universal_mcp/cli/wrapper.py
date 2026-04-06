"""Wrapper utilities to launch external clients with scoped environment injection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from universal_mcp.config.settings import Settings


def build_child_env(extra_env: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(extra_env)
    return env


def run_wrapped_command(command: list[str], extra_env: dict[str, str]) -> int:
    env = build_child_env(extra_env)
    process = subprocess.Popen(command, env=env)
    return process.wait()


def build_wrapper_env(
    *,
    settings: Settings,
    profile_name: str,
    workspace: Path,
) -> dict[str, str]:
    return {
        "UNIVERSAL_MCP_DAEMON_URL": f"http://127.0.0.1:{settings.runtime.port}",
        "UNIVERSAL_MCP_PORT": str(settings.runtime.port),
        "UNIVERSAL_MCP_PROFILE": profile_name,
        "UNIVERSAL_MCP_WORKSPACE": str(workspace),
    }
