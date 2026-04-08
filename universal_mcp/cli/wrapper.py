"""Wrapper utilities to launch external clients with scoped environment injection."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import shutil
from typing import Final

from pydantic import BaseModel, Field

from universal_mcp.config.profiles import ProfileConfig
from universal_mcp.config.settings import Settings

SUPPORTED_CLIENTS: Final[set[str]] = {"codex-cli", "claude-code", "openai"}
CLIENT_DISPLAY_NAMES: Final[dict[str, str]] = {
    "codex-cli": "Codex CLI",
    "claude-code": "Claude Code",
    "openai": "OpenAI",
}
CLIENT_COMMAND_HINTS: Final[dict[str, tuple[str, ...]]] = {
    "codex-cli": ("codex",),
    "claude-code": ("claude",),
    "openai": ("openai",),
}


class WrapperLaunchPlan(BaseModel):
    target_client: str
    display_name: str
    executable: str
    resolved_executable: str | None = None
    launch_message: str
    warnings: list[str] = Field(default_factory=list)


class WrapperValidationError(ValueError):
    """Raised when wrapper launch validation fails."""


def build_child_env(extra_env: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(extra_env)
    return env


def run_wrapped_command(command: list[str], extra_env: dict[str, str]) -> int:
    env = build_child_env(extra_env)
    process = subprocess.Popen(command, env=env)
    return process.wait()


def build_launch_plan(*, command: list[str], target_client: str, workspace: Path) -> WrapperLaunchPlan:
    if not command:
        raise WrapperValidationError(_missing_command_message(target_client=target_client, executable=None))

    if not workspace.exists():
        raise WrapperValidationError(f"El workspace no existe: {workspace}")
    if not workspace.is_dir():
        raise WrapperValidationError(f"El workspace no es un directorio: {workspace}")

    executable = command[0]
    resolved_executable = executable if Path(executable).expanduser().exists() else shutil.which(executable)
    if resolved_executable is None:
        raise WrapperValidationError(_missing_command_message(target_client=target_client, executable=executable))

    warnings: list[str] = []
    display_name = CLIENT_DISPLAY_NAMES.get(target_client, target_client)
    if target_client not in SUPPORTED_CLIENTS:
        warnings.append(f"target client '{target_client}' uses generic wrapper path")
    else:
        hints = CLIENT_COMMAND_HINTS.get(target_client, ())
        executable_name = Path(executable).name.lower()
        if hints and not any(hint in executable_name for hint in hints):
            warnings.append(_client_mismatch_warning(target_client=target_client, executable=Path(executable).name))

    launch_message = f"Launching {display_name} via {Path(executable).name} in {workspace}"

    return WrapperLaunchPlan(
        target_client=target_client,
        display_name=display_name,
        executable=executable,
        resolved_executable=resolved_executable,
        launch_message=launch_message,
        warnings=warnings,
    )


def build_wrapper_env(
    *,
    settings: Settings,
    profile_name: str,
    target_client: str,
    workspace: Path,
) -> dict[str, str]:
    return {
        "UNIVERSAL_MCP_DAEMON_URL": f"http://127.0.0.1:{settings.runtime.port}",
        "UNIVERSAL_MCP_PORT": str(settings.runtime.port),
        "UNIVERSAL_MCP_PROFILE": profile_name,
        "UNIVERSAL_MCP_TARGET_CLIENT": target_client,
        "UNIVERSAL_MCP_TRANSLATION_TARGET": target_client,
        "UNIVERSAL_MCP_WORKSPACE": str(workspace),
    }


def build_wrapper_context(
    *,
    settings: Settings,
    profile_name: str,
    profile: ProfileConfig,
    command: list[str],
    workspace: Path,
) -> tuple[WrapperLaunchPlan, dict[str, str]]:
    plan = build_launch_plan(command=command, target_client=profile.client, workspace=workspace)
    extra_env = build_wrapper_env(
        settings=settings,
        profile_name=profile_name,
        target_client=plan.target_client,
        workspace=workspace,
    )
    extra_env["UNIVERSAL_MCP_CLIENT_EXECUTABLE"] = Path(plan.executable).name
    if plan.resolved_executable is not None:
        extra_env["UNIVERSAL_MCP_CLIENT_EXECUTABLE_PATH"] = plan.resolved_executable
    return plan, extra_env


def _client_mismatch_warning(*, target_client: str, executable: str) -> str:
    if target_client == "codex-cli":
        return (
            f"profile client 'codex-cli' does not match executable '{executable}'. "
            "Hint: para el flujo principal usa `umcp run codex`."
        )
    return f"profile client '{target_client}' does not match executable '{executable}'"


def _missing_command_message(*, target_client: str, executable: str | None) -> str:
    if target_client == "codex-cli":
        command_name = executable or "codex"
        return (
            f"Comando no encontrado: {command_name}. "
            "Para Codex CLI instala `codex` o añádelo al PATH, y usa `umcp run codex`."
        )
    if executable is None:
        return "Debes indicar un comando externo para ejecutar"
    return f"Comando no encontrado: {executable}"
