from pathlib import Path

from universal_mcp.observability.events import EventRecord
from universal_mcp.observability.logging import append_event, read_events


def test_append_and_read_events_roundtrip(tmp_path: Path) -> None:
    append_event(
        EventRecord(
            level="info",
            component="daemon",
            event="started",
            message="daemon started",
            mcp_name="git",
        ),
        root=tmp_path,
    )
    append_event(
        EventRecord(
            level="error",
            component="daemon",
            event="failed",
            message="daemon failed",
            mcp_name="github",
        ),
        root=tmp_path,
    )

    all_events = read_events(tmp_path)
    error_events = read_events(tmp_path, level="error")
    git_events = read_events(tmp_path, mcp_name="git")

    assert len(all_events) == 2
    assert len(error_events) == 1
    assert error_events[0].event == "failed"
    assert len(git_events) == 1
    assert git_events[0].mcp_name == "git"

