from universal_mcp.daemon.memory_filter import (
    DEFAULT_MAX_PAGE_ITEMS,
    apply_response_policy,
    paginate_list,
    truncate_large_fields,
    truncate_lines,
    truncate_text,
)


def test_truncate_text_marks_truncation() -> None:
    text = "a" * 20
    truncated, metadata = truncate_text(text, max_bytes=8, policy_name="test")
    assert truncated == "a" * 8
    assert metadata.truncated is True
    assert metadata.policy_applied == "test"


def test_truncate_lines_respects_line_limit() -> None:
    text = "\n".join(str(i) for i in range(10))
    truncated, metadata = truncate_lines(
        text,
        max_bytes=1024,
        max_lines=3,
        policy_name="test-lines",
    )
    assert truncated == "0\n1\n2"
    assert metadata.truncated is True


def test_paginate_list_returns_next_cursor() -> None:
    items = list(range(DEFAULT_MAX_PAGE_ITEMS + 5))
    page, metadata = paginate_list(items)
    assert len(page) == DEFAULT_MAX_PAGE_ITEMS
    assert metadata.next_cursor == str(DEFAULT_MAX_PAGE_ITEMS)
    assert metadata.truncated is True


def test_truncate_large_fields_only_trims_big_strings() -> None:
    payload, metadata = truncate_large_fields(
        {"small": "ok", "big": "x" * 9000},
        max_field_bytes=16,
    )
    assert payload["small"] == "ok"
    assert payload["big"] == "x" * 16
    assert metadata.truncated is True


def test_apply_response_policy_for_list_uses_pagination() -> None:
    page, metadata = apply_response_policy(list(range(150)))
    assert len(page) == 100
    assert metadata.next_cursor == "100"

