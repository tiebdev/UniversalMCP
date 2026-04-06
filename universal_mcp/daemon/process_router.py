"""Supervisor for managed MCP child processes."""

from __future__ import annotations

import asyncio
import os
import shutil
from datetime import datetime, timedelta, timezone

from universal_mcp.config.catalog import CatalogEntry, IntegrationKind
from universal_mcp.daemon.external_mcp import ExternalMcpSession
from universal_mcp.daemon.health import check_process_health
from universal_mcp.daemon.state import ManagedProcessStatus, ProcessState

MAX_RESTARTS = 3
BASE_BACKOFF_SECONDS = 1.0


class ProcessRouter:
    """Owns subprocess supervision for managed MCP entries."""

    def __init__(
        self,
        catalog: list[CatalogEntry],
        *,
        env_by_name: dict[str, dict[str, str]] | None = None,
        preflight_errors_by_name: dict[str, list[str]] | None = None,
    ) -> None:
        self._catalog = {entry.name: entry for entry in catalog}
        self._statuses = {
            entry.name: ManagedProcessStatus(name=entry.name, state=ProcessState.STOPPED)
            for entry in catalog
        }
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._sessions: dict[str, ExternalMcpSession] = {}
        self._restart_attempts: dict[str, int] = {entry.name: 0 for entry in catalog}
        self._next_restart_at: dict[str, datetime | None] = {entry.name: None for entry in catalog}
        self._env_by_name = env_by_name or {}
        self._preflight_errors_by_name = preflight_errors_by_name or {}
        self._manually_stopped: set[str] = set()

    def list_statuses(self) -> list[ManagedProcessStatus]:
        return list(self._statuses.values())

    def get_status(self, name: str) -> ManagedProcessStatus:
        return self._statuses[name]

    def managed_names(self) -> list[str]:
        return list(self._catalog.keys())

    async def start_all(self) -> None:
        for name in self._catalog:
            await self.start_process(name)

    async def start_process(self, name: str, *, is_restart: bool = False) -> None:
        entry = self._catalog[name]
        status = self._statuses[name]
        executable = shutil.which(entry.command)

        status.updated_at = self._utcnow()
        status.state = ProcessState.STARTING
        status.last_error = None

        preflight_errors = self._preflight_errors_by_name.get(name, [])
        if preflight_errors:
            status.state = ProcessState.FAILED
            status.last_error = "; ".join(preflight_errors)
            status.updated_at = self._utcnow()
            return

        if executable is None:
            status.state = ProcessState.FAILED
            status.last_error = f"Command not available: {entry.command}"
            status.updated_at = self._utcnow()
            return

        env = os.environ.copy()
        env.update(self._env_by_name.get(name, {}))

        try:
            process = await asyncio.create_subprocess_exec(
                executable,
                *entry.args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                stdin=asyncio.subprocess.PIPE,
                env=env,
            )
        except OSError as exc:
            status.state = ProcessState.FAILED
            status.last_error = str(exc)
            status.updated_at = self._utcnow()
            return

        self._processes[name] = process
        session = ExternalMcpSession(name, process)
        self._sessions[name] = session
        self._manually_stopped.discard(name)
        status.pid = process.pid
        status.started_at = self._utcnow()

        if is_restart:
            status.restart_count += 1

        await asyncio.sleep(0)
        if process.returncode is not None:
            self._schedule_restart_or_fail(name, process.returncode)
        elif entry.integration_kind != IntegrationKind.EXTERNAL:
            status.state = ProcessState.HEALTHY
            status.last_healthy_at = self._utcnow()
            self._next_restart_at[name] = None
        else:
            try:
                await session.initialize()
            except Exception as exc:
                status.state = ProcessState.FAILED
                status.last_error = f"Initialization failed: {exc}"
            else:
                status.state = ProcessState.HEALTHY
                status.last_healthy_at = self._utcnow()
                self._next_restart_at[name] = None

        status.updated_at = self._utcnow()

    async def refresh_statuses(self) -> None:
        for name, status in self._statuses.items():
            process = self._processes.get(name)
            health = await check_process_health(name, process, status)

            if health.ok:
                status.state = ProcessState.HEALTHY
                status.last_healthy_at = self._utcnow()
                status.updated_at = status.last_healthy_at
                continue

            if name in self._manually_stopped:
                status.state = ProcessState.STOPPED
                status.pid = None
                status.updated_at = self._utcnow()
                continue

            if process is not None and process.returncode is not None:
                self._schedule_restart_or_fail(name, process.returncode)
                scheduled = self._next_restart_at.get(name)
                if scheduled and self._utcnow() >= scheduled:
                    await self.start_process(name, is_restart=True)
            elif health.state == "stopped":
                status.state = ProcessState.STOPPED
            else:
                status.state = ProcessState.DEGRADED

            status.updated_at = self._utcnow()

    async def snapshot(self) -> list[ManagedProcessStatus]:
        await self.refresh_statuses()
        return self.list_statuses()

    async def stop_process(self, name: str) -> None:
        process = self._processes.get(name)
        status = self._statuses[name]
        self._manually_stopped.add(name)
        self._next_restart_at[name] = None
        self._restart_attempts[name] = 0

        if process is None:
            status.state = ProcessState.STOPPED
            status.pid = None
            status.updated_at = self._utcnow()
            return

        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

        status.state = ProcessState.STOPPED
        status.pid = None
        status.updated_at = self._utcnow()
        self._processes.pop(name, None)
        self._sessions.pop(name, None)

    async def restart_process(self, name: str) -> ManagedProcessStatus:
        await self.stop_process(name)
        await self.start_process(name, is_restart=True)
        await self.refresh_statuses()
        return self._statuses[name]

    async def stop_all(self) -> None:
        for name in list(self._statuses):
            await self.stop_process(name)

    async def list_tools(self, name: str, cursor: str | None = None) -> dict[str, Any]:
        session = self._sessions.get(name)
        if session is None:
            raise RuntimeError(f"No active session for MCP: {name}")
        return await session.list_tools(cursor)

    async def call_tool(self, name: str, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        session = self._sessions.get(name)
        if session is None:
            raise RuntimeError(f"No active session for MCP: {name}")
        return await session.call_tool(tool_name, arguments)

    def _schedule_restart_or_fail(self, name: str, returncode: int) -> None:
        status = self._statuses[name]
        attempts = self._restart_attempts[name]

        if attempts >= MAX_RESTARTS:
            status.state = ProcessState.FAILED
            status.last_error = f"Process exited with code {returncode}; restart limit reached"
            self._next_restart_at[name] = None
            return

        delay_seconds = BASE_BACKOFF_SECONDS * (2**attempts)
        self._restart_attempts[name] = attempts + 1
        self._next_restart_at[name] = self._utcnow() + timedelta(seconds=delay_seconds)
        status.state = ProcessState.DEGRADED
        status.last_error = (
            f"Process exited with code {returncode}; restart scheduled in {delay_seconds:.0f}s"
        )

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)
