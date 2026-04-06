from pathlib import Path

from typer.testing import CliRunner

from universal_mcp.cli.main import app
from universal_mcp.observability.events import EventRecord
from universal_mcp.observability.logging import append_event


runner = CliRunner()


def test_logs_command_reads_filtered_events() -> None:
    with runner.isolated_filesystem():
        append_event(
            EventRecord(
                level="info",
                component="daemon",
                event="started",
                message="daemon started",
                mcp_name="git",
            ),
            root=Path.cwd(),
        )
        append_event(
            EventRecord(
                level="error",
                component="daemon",
                event="failed",
                message="daemon failed",
                mcp_name="github",
            ),
            root=Path.cwd(),
        )

        result = runner.invoke(app, ["logs", "--level", "error"])
        assert result.exit_code == 0
        assert "daemon:failed" in result.stdout
        assert "daemon started" not in result.stdout
