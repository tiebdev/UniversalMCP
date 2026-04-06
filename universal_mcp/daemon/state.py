"""Shared runtime state models for the daemon."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProcessState(str, Enum):
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


class ManagedProcessStatus(BaseModel):
    """Observed status for one managed MCP process."""

    name: str
    state: ProcessState = ProcessState.STOPPED
    pid: int | None = None
    restart_count: int = 0
    started_at: datetime | None = None
    last_healthy_at: datetime | None = None
    last_error: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)


class DaemonStatus(BaseModel):
    """High-level daemon status shown by the CLI."""

    port: int
    started_at: datetime = Field(default_factory=utcnow)
    default_profile: str | None = None
    processes: list[ManagedProcessStatus] = Field(default_factory=list)


class ExternalMcpPreflight(BaseModel):
    """Configuration and readiness information for an external MCP."""

    name: str
    enabled: bool
    executable_available: bool
    required_env_present: bool
    env_keys: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    process_state: ProcessState | None = None
