"""Profile models for settings and runtime selection."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspacePolicy(BaseModel):
    mode: str = "explicit"


class ServiceConfig(BaseModel):
    secret_ref: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None


class ProfileConfig(BaseModel):
    client: str = "codex-cli"
    enabled_mcps: list[str] = Field(default_factory=list)
    workspace_policy: WorkspacePolicy = Field(default_factory=WorkspacePolicy)
    services: dict[str, ServiceConfig] = Field(default_factory=dict)
