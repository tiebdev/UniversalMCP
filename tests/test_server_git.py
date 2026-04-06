import asyncio
from pathlib import Path
import subprocess

from universal_mcp.daemon.server import create_git_handlers


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
        text=True,
    )


def _log_event(**kwargs) -> None:
    return None


def test_git_handlers_work_inside_workspace(tmp_path: Path) -> None:
    async def runner() -> None:
        _init_repo(tmp_path)
        file_path = tmp_path / "demo.txt"
        file_path.write_text("first", encoding="utf-8")
        (
            status_handler,
            diff_handler,
            changed_files_handler,
            branch_handler,
            log_handler,
            show_handler,
            diff_file_handler,
        ) = create_git_handlers(tmp_path, _log_event)

        status = await status_handler(None)
        assert status["branch"] in {"master", "main"}
        assert "demo.txt" in status["porcelain"]
        changed = await changed_files_handler(None)
        assert changed["files"] == ["demo.txt"]
        branch = await branch_handler(None)
        assert branch["branch"] in {"master", "main"}

        subprocess.run(["git", "-C", str(tmp_path), "add", "demo.txt"], check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "demo"],
            check=True,
            capture_output=True,
            text=True,
        )
        file_path.write_text("second", encoding="utf-8")
        diff = await diff_handler(None, False)
        assert "+second" in diff["diff"]
        diff_file = await diff_file_handler(None, "demo.txt", False)
        assert "+second" in diff_file["diff"]

        log_result = await log_handler(None, 1)
        assert log_result["entries"][0]["subject"] == "demo"

        commit = log_result["entries"][0]["commit"]
        show_result = await show_handler(None, commit)
        assert "demo" in show_result["patch"]

    asyncio.run(runner())
