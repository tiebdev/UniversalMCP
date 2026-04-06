import asyncio
import sys

from universal_mcp.daemon.health import check_process_health
from universal_mcp.daemon.state import ManagedProcessStatus, ProcessState


def test_check_process_health_alive_process() -> None:
    async def runner() -> None:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import time; time.sleep(1)",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        status = ManagedProcessStatus(name="demo", state=ProcessState.HEALTHY, pid=process.pid)
        health = await check_process_health("demo", process, status)
        process.terminate()
        await process.wait()
        assert health.ok is True
        assert health.state == "healthy"

    asyncio.run(runner())

