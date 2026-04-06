"""Schema normalization and translation layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TranslationEnvelope(BaseModel):
    """Translated payload plus metadata about the target client."""

    target_client: str
    payload: dict[str, Any]
    normalized: bool = True
    warnings: list[str] = Field(default_factory=list)


def _normalize_tool_name(name: str | None) -> str:
    if not name:
        return "unnamed_tool"
    return name.strip().replace(" ", "_").replace("-", "_")


def _normalize_tool_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    normalized = dict(payload)

    tool_name = normalized.get("tool_name") or normalized.get("name")
    normalized["name"] = _normalize_tool_name(tool_name)

    if "tool_name" in normalized:
        normalized.pop("tool_name")

    if "input_schema" not in normalized:
        schema = normalized.pop("parameters", None) or {"type": "object", "properties": {}}
        normalized["input_schema"] = schema
        warnings.append("input_schema synthesized from parameters or default object schema")

    if "description" not in normalized:
        normalized["description"] = ""
        warnings.append("description missing; defaulted to empty string")

    return normalized, warnings


def _translate_for_codex_cli(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


def _translate_for_openai(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": payload["name"],
            "description": payload.get("description", ""),
            "parameters": payload.get("input_schema", {"type": "object", "properties": {}}),
        },
    }


def _translate_for_generic(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


def translate_payload(payload: dict[str, Any], *, target_client: str) -> TranslationEnvelope:
    normalized, warnings = _normalize_tool_payload(payload)

    if target_client == "codex-cli":
        translated = _translate_for_codex_cli(normalized)
    elif target_client == "claude-code":
        translated = _translate_for_codex_cli(normalized)
        warnings.append("claude-code path retained as compatibility alias")
    elif target_client == "openai":
        translated = _translate_for_openai(normalized)
    else:
        translated = _translate_for_generic(normalized)
        warnings.append(f"target client '{target_client}' uses generic translation path")

    return TranslationEnvelope(
        target_client=target_client,
        payload=translated,
        warnings=warnings,
    )
