"""Local JSON logging utilities."""

from __future__ import annotations

import json
from pathlib import Path

from universal_mcp.observability.events import EventRecord
from universal_mcp.runtime.paths import events_file, runtime_dir


def serialize_event(event: EventRecord) -> str:
    return json.dumps(event.model_dump(mode="json"), ensure_ascii=True)


def append_event(event: EventRecord, root: Path | None = None) -> Path:
    directory = runtime_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = events_file(root)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(serialize_event(event))
        fh.write("\n")
    return path


def read_events(
    root: Path | None = None,
    *,
    level: str | None = None,
    mcp_name: str | None = None,
) -> list[EventRecord]:
    path = events_file(root)
    if not path.exists():
        return []

    events: list[EventRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = EventRecord.model_validate_json(line)
        if level and event.level != level:
            continue
        if mcp_name and event.mcp_name != mcp_name:
            continue
        events.append(event)
    return events
