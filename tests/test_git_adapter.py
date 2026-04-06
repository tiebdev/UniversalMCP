from pathlib import Path
import subprocess

from universal_mcp.daemon.git_adapter import (
    git_branch,
    git_changed_files,
    git_diff,
    git_diff_file,
    git_log,
    git_show,
    git_status,
)


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


def test_git_status_reads_branch_and_porcelain(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    response = git_status(tmp_path)
    assert response.branch in {"master", "main"}
    assert "a.txt" in response.porcelain


def test_git_diff_returns_changed_content(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    target = tmp_path / "a.txt"
    target.write_text("one", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.txt"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "init"],
        check=True,
        capture_output=True,
        text=True,
    )
    target.write_text("two", encoding="utf-8")
    response = git_diff(tmp_path)
    assert "--- a/a.txt" in response.diff
    assert "+two" in response.diff


def test_git_changed_files_and_branch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    target = tmp_path / "a.txt"
    target.write_text("one", encoding="utf-8")
    changed = git_changed_files(tmp_path)
    branch = git_branch(tmp_path)
    assert changed.files == ["a.txt"]
    assert branch.branch in {"master", "main"}


def test_git_log_and_show_return_commit_data(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    target = tmp_path / "a.txt"
    target.write_text("one", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.txt"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "init commit"],
        check=True,
        capture_output=True,
        text=True,
    )
    log_response = git_log(tmp_path, limit=1)
    assert len(log_response.entries) == 1
    assert log_response.entries[0].subject == "init commit"

    show_response = git_show(tmp_path, log_response.entries[0].commit)
    assert "init commit" in show_response.patch
    assert "a.txt" in show_response.patch


def test_git_diff_file_scopes_to_single_path(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("one", encoding="utf-8")
    second.write_text("uno", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.txt", "b.txt"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "base"],
        check=True,
        capture_output=True,
        text=True,
    )
    first.write_text("two", encoding="utf-8")
    second.write_text("dos", encoding="utf-8")
    response = git_diff_file(tmp_path, "a.txt")
    assert "a/a.txt" in response.diff
    assert "b/b.txt" not in response.diff
