import asyncio
import sys
from pathlib import Path

from universal_mcp.config.catalog import CatalogEntry, IntegrationKind, RiskLevel, SharingMode
from universal_mcp.daemon.process_router import ProcessRouter
from universal_mcp.daemon.state import ProcessState


MOCK_SERVER = """
import json, sys
initialized = False
for line in sys.stdin:
    msg = json.loads(line)
    method = msg.get("method")
    if method == "initialize":
        sys.stdout.write(json.dumps({
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mock", "version": "1.0.0"}
            }
        }) + "\\n")
        sys.stdout.flush()
    elif method == "notifications/initialized":
        initialized = True
    elif method == "tools/list":
        sys.stdout.write(json.dumps({
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "tools": [
                    {
                        "name": "echo_tool",
                        "description": "Echo input",
                        "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}
                    }
                ]
            }
        }) + "\\n")
        sys.stdout.flush()
    elif method == "tools/call":
        sys.stdout.write(json.dumps({
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "content": [{"type": "text", "text": str(msg.get("params", {}).get("arguments", {}))}],
                "isError": False
            }
        }) + "\\n")
        sys.stdout.flush()
"""


def test_external_mcp_session_list_tools_and_call() -> None:
    async def runner() -> None:
        router = ProcessRouter(
            [
                CatalogEntry(
                    name="mock-external",
                    command=sys.executable,
                    args=["-c", MOCK_SERVER],
                    risk=RiskLevel.LOW,
                    sharing_mode=SharingMode.GLOBAL,
                    integration_kind=IntegrationKind.EXTERNAL,
                )
            ]
        )
        await router.start_all()
        status = router.get_status("mock-external")
        assert status.state == ProcessState.HEALTHY

        tools = await router.list_tools("mock-external")
        assert tools["tools"][0]["name"] == "echo_tool"

        result = await router.call_tool("mock-external", "echo_tool", {"text": "hi"})
        assert result["isError"] is False
        assert "hi" in result["content"][0]["text"]

        await router.stop_all()

    asyncio.run(runner())
