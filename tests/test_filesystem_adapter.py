from pathlib import Path

import pytest

from universal_mcp.daemon.filesystem_adapter import (
    glob_paths,
    list_directory,
    path_exists,
    read_file,
    read_many,
    search_text,
    stat_path,
)


def test_list_directory_returns_entries(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "subdir").mkdir()
    result = list_directory(tmp_path)
    names = [entry.name for entry in result.entries]
    assert names == ["a.txt", "subdir"]


def test_read_file_returns_partial_content(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello world", encoding="utf-8")
    result = read_file(tmp_path, "a.txt", offset=6, max_bytes=5)
    assert result.content == "world"
    assert result.bytes_read == 5


def test_adapter_blocks_escape_from_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        read_file(tmp_path, "../outside.txt")


def test_exists_and_stat_report_file_metadata(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    exists = path_exists(tmp_path, "a.txt")
    stat = stat_path(tmp_path, "a.txt")
    assert exists.exists is True
    assert exists.entry_type == "file"
    assert stat.size == 5


def test_glob_paths_filters_matching_files(tmp_path: Path) -> None:
    (tmp_path / "alpha.py").write_text("x", encoding="utf-8")
    (tmp_path / "beta.txt").write_text("y", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "gamma.py").write_text("z", encoding="utf-8")
    result = glob_paths(tmp_path, "*.py")
    assert [match.path for match in result.matches] == ["alpha.py", "sub/gamma.py"]


def test_search_text_returns_match_locations(tmp_path: Path) -> None:
    (tmp_path / "alpha.py").write_text("one\nreturn value\nthree\n", encoding="utf-8")
    result = search_text(tmp_path, ".", "return")
    assert len(result.matches) == 1
    assert result.matches[0].path == "alpha.py"
    assert result.matches[0].line == 2


def test_read_many_returns_multiple_files(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta", encoding="utf-8")
    result = read_many(tmp_path, ["a.txt", "b.txt"], max_bytes_each=4)
    assert [item.content for item in result.items] == ["alph", "beta"]
