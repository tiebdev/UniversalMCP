import asyncio
import sys

from universal_mcp.config.catalog import CatalogEntry, IntegrationKind, RiskLevel, SharingMode
from universal_mcp.daemon.process_router import ProcessRouter
from universal_mcp.daemon.state import ProcessState


def test_process_router_marks_missing_command_as_failed() -> None:
    async def runner() -> None:
        router = ProcessRouter(
            [
                CatalogEntry(
                    name="missing",
                    command="definitely-not-a-real-command",
                    risk=RiskLevel.LOW,
                    sharing_mode=SharingMode.GLOBAL,
                )
            ]
        )
        await router.start_all()
        statuses = router.list_statuses()
        assert len(statuses) == 1
        assert statuses[0].state == ProcessState.FAILED
        assert "Command not available" in (statuses[0].last_error or "")

    asyncio.run(runner())


def test_process_router_starts_and_stops_real_process() -> None:
    async def runner() -> None:
        router = ProcessRouter(
            [
                CatalogEntry(
                    name="sleeper",
                    command=sys.executable,
                    args=["-c", "import time; time.sleep(5)"],
                    risk=RiskLevel.LOW,
                    sharing_mode=SharingMode.GLOBAL,
                    integration_kind=IntegrationKind.INTERNAL,
                )
            ]
        )
        await router.start_all()
        statuses = await router.snapshot()
        assert statuses[0].state == ProcessState.HEALTHY
        assert statuses[0].pid is not None
        await router.stop_all()
        stopped = router.list_statuses()[0]
        assert stopped.state == ProcessState.STOPPED

    asyncio.run(runner())
