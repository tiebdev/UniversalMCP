import asyncio
from pathlib import Path

from universal_mcp.daemon.server import create_filesystem_handlers


def _log_event(**kwargs) -> None:
    return None


def test_filesystem_handlers_work_inside_workspace(tmp_path: Path) -> None:
    async def runner() -> None:
        (tmp_path / "alpha.txt").write_text("abcdef", encoding="utf-8")
        (
            list_handler,
            read_handler,
            exists_handler,
            stat_handler,
            glob_handler,
            search_handler,
            read_many_handler,
        ) = create_filesystem_handlers(tmp_path, _log_event)

        listing = await list_handler(".", None)
        assert listing["entries"][0]["name"] == "alpha.txt"

        read = await read_handler("alpha.txt", None, 2, 3)
        assert read["content"] == "cde"

        exists = await exists_handler("alpha.txt", None)
        assert exists["exists"] is True

        stat = await stat_handler("alpha.txt", None)
        assert stat["size"] == 6

        globbed = await glob_handler("*.txt", None)
        assert globbed["matches"][0]["name"] == "alpha.txt"

        search = await search_handler(".", None, "cde", 10)
        assert search["matches"][0]["path"] == "alpha.txt"

        read_many = await read_many_handler(["alpha.txt"], None, 4)
        assert read_many["items"][0]["content"] == "abcd"

    asyncio.run(runner())
