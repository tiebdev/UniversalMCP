"""Structured event models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventRecord(BaseModel):
    timestamp: datetime = Field(default_factory=utcnow)
    level: str
    component: str
    event: str
    message: str
    profile: str | None = None
    workspace: str | None = None
    mcp_name: str | None = None
    process_state: str | None = None
    request_id: str | None = None
    error_type: str | None = None

