"""Response truncation and pagination policies for daemon output."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


DEFAULT_MAX_RESPONSE_BYTES = 64 * 1024
DEFAULT_MAX_LOG_BYTES = 32 * 1024
DEFAULT_MAX_LOG_LINES = 400
DEFAULT_MAX_DIFF_BYTES = 48 * 1024
DEFAULT_MAX_DIFF_LINES = 600
DEFAULT_MAX_PAGE_ITEMS = 100
DEFAULT_MAX_FIELD_BYTES = 8 * 1024


@dataclass(slots=True)
class FilterMetadata:
    truncated: bool
    original_size_estimate: int
    returned_size: int
    policy_applied: str
    next_cursor: str | None = None


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=True).encode("utf-8"))


def truncate_text(text: str, *, max_bytes: int, policy_name: str) -> tuple[str, FilterMetadata]:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, FilterMetadata(
            truncated=False,
            original_size_estimate=len(encoded),
            returned_size=len(encoded),
            policy_applied=policy_name,
        )

    truncated_bytes = encoded[:max_bytes]
    truncated_text = truncated_bytes.decode("utf-8", errors="ignore")
    returned_size = len(truncated_text.encode("utf-8"))
    return truncated_text, FilterMetadata(
        truncated=True,
        original_size_estimate=len(encoded),
        returned_size=returned_size,
        policy_applied=policy_name,
    )


def truncate_lines(
    text: str,
    *,
    max_bytes: int,
    max_lines: int,
    policy_name: str,
) -> tuple[str, FilterMetadata]:
    original_size = len(text.encode("utf-8"))
    lines = text.splitlines()
    truncated_by_lines = len(lines) > max_lines
    candidate = "\n".join(lines[:max_lines]) if truncated_by_lines else text

    if len(candidate.encode("utf-8")) > max_bytes:
        candidate, metadata = truncate_text(candidate, max_bytes=max_bytes, policy_name=policy_name)
        metadata.original_size_estimate = original_size
        return candidate, metadata

    return candidate, FilterMetadata(
        truncated=truncated_by_lines,
        original_size_estimate=original_size,
        returned_size=len(candidate.encode("utf-8")),
        policy_applied=policy_name,
    )


def paginate_list(
    items: list[Any],
    *,
    limit: int = DEFAULT_MAX_PAGE_ITEMS,
    cursor: str | None = None,
    policy_name: str = "paginate:list",
) -> tuple[list[Any], FilterMetadata]:
    start = int(cursor) if cursor else 0
    end = start + limit
    page = items[start:end]
    next_cursor = str(end) if end < len(items) else None
    original_size = _json_size(items)
    returned_size = _json_size(page)
    return page, FilterMetadata(
        truncated=next_cursor is not None,
        original_size_estimate=original_size,
        returned_size=returned_size,
        policy_applied=policy_name,
        next_cursor=next_cursor,
    )


def truncate_large_fields(
    payload: dict[str, Any],
    *,
    max_field_bytes: int = DEFAULT_MAX_FIELD_BYTES,
    policy_name: str = "truncate:fields",
) -> tuple[dict[str, Any], FilterMetadata]:
    result: dict[str, Any] = {}
    truncated = False
    for key, value in payload.items():
        if isinstance(value, str):
            trimmed, metadata = truncate_text(
                value,
                max_bytes=max_field_bytes,
                policy_name=f"{policy_name}:{key}",
            )
            result[key] = trimmed
            truncated = truncated or metadata.truncated
        else:
            result[key] = value

    return result, FilterMetadata(
        truncated=truncated,
        original_size_estimate=_json_size(payload),
        returned_size=_json_size(result),
        policy_applied=policy_name,
    )


def apply_response_policy(
    payload: Any,
    *,
    kind: str = "generic",
    cursor: str | None = None,
) -> tuple[Any, FilterMetadata]:
    if isinstance(payload, str):
        if kind == "log":
            return truncate_lines(
                payload,
                max_bytes=DEFAULT_MAX_LOG_BYTES,
                max_lines=DEFAULT_MAX_LOG_LINES,
                policy_name="truncate:log",
            )
        if kind == "diff":
            return truncate_lines(
                payload,
                max_bytes=DEFAULT_MAX_DIFF_BYTES,
                max_lines=DEFAULT_MAX_DIFF_LINES,
                policy_name="truncate:diff",
            )
        return truncate_text(
            payload,
            max_bytes=DEFAULT_MAX_RESPONSE_BYTES,
            policy_name="truncate:generic",
        )

    if isinstance(payload, list):
        return paginate_list(
            payload,
            limit=DEFAULT_MAX_PAGE_ITEMS,
            cursor=cursor,
            policy_name="paginate:list",
        )

    if isinstance(payload, dict):
        trimmed, field_metadata = truncate_large_fields(payload)
        if field_metadata.returned_size <= DEFAULT_MAX_RESPONSE_BYTES:
            return trimmed, field_metadata

        json_payload = json.dumps(trimmed, ensure_ascii=True)
        truncated_json, metadata = truncate_text(
            json_payload,
            max_bytes=DEFAULT_MAX_RESPONSE_BYTES,
            policy_name="truncate:object-json",
        )
        return {"partial_json": truncated_json}, metadata

    metadata = FilterMetadata(
        truncated=False,
        original_size_estimate=_json_size(payload),
        returned_size=_json_size(payload),
        policy_applied="pass-through",
    )
    return payload, metadata
