"""Shared execution layer for internal MCP-style tools."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from universal_mcp.daemon.memory_filter import apply_response_policy


def resolve_workspace(root: Path, workspace: str | None = None) -> Path:
    candidate = Path(workspace).resolve() if workspace else root.resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("Workspace escapes daemon root")
    return candidate


def format_filter_metadata(metadata) -> dict[str, Any]:
    return {
        "truncated": metadata.truncated,
        "original_size_estimate": metadata.original_size_estimate,
        "returned_size": metadata.returned_size,
        "policy_applied": metadata.policy_applied,
        "next_cursor": metadata.next_cursor,
    }


def build_internal_tool_executor(root: Path, log_event: Callable[..., None]):
    async def execute(
        *,
        tool_name: str,
        event_name: str,
        message: str,
        workspace: str | None,
        kind: str,
        operation: Callable[[Path], Any],
        response_builder: Callable[[Any, str], tuple[dict[str, Any], Any]],
        filtered_field: str | None = None,
    ) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        workspace_root = resolve_workspace(root, workspace)
        response = operation(workspace_root)
        payload, raw_for_filter = response_builder(response, request_id)
        filtered_value, metadata = apply_response_policy(raw_for_filter, kind=kind)
        payload["filter_metadata"] = format_filter_metadata(metadata)

        if filtered_field is not None:
            payload[filtered_field] = filtered_value
        elif kind in {"generic", "diff", "log"}:
            if "entries" in payload:
                payload["entries"] = filtered_value
            elif "content" in payload:
                payload["content"] = filtered_value
            elif "porcelain" in payload:
                payload["porcelain"] = filtered_value
            elif "diff" in payload:
                payload["diff"] = filtered_value

        log_event(
            level="info",
            component=tool_name,
            event=event_name,
            message=message,
            request_id=request_id,
            mcp_name=tool_name,
        )
        return payload

    return execute
