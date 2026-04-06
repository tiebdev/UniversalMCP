"""Common stdio MCP client for external managed servers."""

from __future__ import annotations

import asyncio
import json
from typing import Any


class ExternalMcpSession:
    """Minimal stdio JSON-RPC client for newline-delimited MCP servers."""

    def __init__(self, name: str, process: asyncio.subprocess.Process) -> None:
        self.name = name
        self.process = process
        self._request_id = 0
        self._lock = asyncio.Lock()

    async def initialize(self) -> dict[str, Any]:
        result = await self.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "universal-mcp", "version": "0.1.0"},
            },
        )
        await self.notify("notifications/initialized", {})
        return result

    async def list_tools(self, cursor: str | None = None) -> dict[str, Any]:
        params = {"cursor": cursor} if cursor else {}
        return await self.request("tools/list", params)

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"name": name}
        if arguments is not None:
            params["arguments"] = arguments
        return await self.request("tools/call", params)

    async def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._lock:
            self._request_id += 1
            request_id = self._request_id
            payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
            if params is not None:
                payload["params"] = params
            await self._send(payload)

            while True:
                message = await self._read_message()
                if message.get("id") != request_id:
                    continue
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message.get("result", {})

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        await self._send(payload)

    async def _send(self, message: dict[str, Any]) -> None:
        if self.process.stdin is None:
            raise RuntimeError(f"{self.name} stdin unavailable")
        line = json.dumps(message, ensure_ascii=True) + "\n"
        self.process.stdin.write(line.encode("utf-8"))
        await self.process.stdin.drain()

    async def _read_message(self) -> dict[str, Any]:
        if self.process.stdout is None:
            raise RuntimeError(f"{self.name} stdout unavailable")
        line = await self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"{self.name} closed stdout")
        return json.loads(line.decode("utf-8"))
