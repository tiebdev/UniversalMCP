from universal_mcp.daemon.translator import translate_payload


def test_translate_payload_normalizes_tool_for_codex() -> None:
    translated = translate_payload(
        {
            "tool_name": "My Tool",
            "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
        },
        target_client="codex-cli",
    )
    assert translated.payload["name"] == "My_Tool"
    assert "input_schema" in translated.payload
    assert translated.normalized is True


def test_translate_payload_maps_to_openai_shape() -> None:
    translated = translate_payload(
        {
            "name": "lookup",
            "description": "Lookup things",
            "input_schema": {"type": "object", "properties": {}},
        },
        target_client="openai",
    )
    assert translated.payload["type"] == "function"
    assert translated.payload["function"]["name"] == "lookup"


def test_translate_payload_warns_on_generic_target() -> None:
    translated = translate_payload({"name": "demo"}, target_client="generic-client")
    assert translated.payload["name"] == "demo"
    assert translated.warnings
