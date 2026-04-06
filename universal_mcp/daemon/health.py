"""Health-check contracts for managed MCP processes."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from universal_mcp.daemon.state import ManagedProcessStatus, ProcessState


class HealthCheckResult(BaseModel):
    """Basic health-check response used by the supervisor."""

    ok: bool
    message: str | None = None
    state: str = "healthy"


async def check_process_health(
    name: str,
    process: asyncio.subprocess.Process | None,
    status: ManagedProcessStatus,
) -> HealthCheckResult:
    """Basic process-oriented health check for V1.

    V1 only verifies process liveness and recent status markers.
    """

    if process is None:
        return HealthCheckResult(ok=False, message=f"{name} is not running", state="stopped")

    if process.returncode is None:
        return HealthCheckResult(ok=True, message=f"{name} process alive", state="healthy")

    if status.state == ProcessState.DEGRADED:
        return HealthCheckResult(
            ok=False,
            message=status.last_error or f"{name} degraded",
            state="degraded",
        )

    return HealthCheckResult(
        ok=False,
        message=status.last_error or f"{name} exited with code {process.returncode}",
        state="failed",
    )
