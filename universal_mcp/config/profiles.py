"""Profile models for settings and runtime selection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic import model_validator


class WorkspacePolicy(BaseModel):
    mode: Literal["explicit", "fixed"] = "explicit"
    path: str | None = None

    @model_validator(mode="after")
    def validate_path_requirements(self) -> "WorkspacePolicy":
        if self.mode == "explicit" and self.path is not None:
            raise ValueError("workspace_policy.path must be empty when mode is 'explicit'")
        if self.mode == "fixed" and not self.path:
            raise ValueError("workspace_policy.path is required when mode is 'fixed'")
        return self


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
