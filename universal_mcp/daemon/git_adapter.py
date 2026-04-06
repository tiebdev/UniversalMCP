"""Internal git adapter used as the second real MCP integration."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel


class GitStatusResponse(BaseModel):
    root: str
    branch: str
    porcelain: str


class GitDiffResponse(BaseModel):
    root: str
    diff: str


class GitChangedFilesResponse(BaseModel):
    root: str
    files: list[str]


class GitBranchResponse(BaseModel):
    root: str
    branch: str


class GitLogEntry(BaseModel):
    commit: str
    author_name: str
    author_email: str
    subject: str


class GitLogResponse(BaseModel):
    root: str
    entries: list[GitLogEntry]


class GitShowResponse(BaseModel):
    root: str
    commit: str
    patch: str


def _resolve_workspace(root: Path, workspace: str | None = None) -> Path:
    candidate = Path(workspace).resolve() if workspace else root.resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("Workspace escapes daemon root")
    return candidate


def _run_git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(workspace), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise RuntimeError(message)
    return completed.stdout


def git_status(root: Path, workspace: str | None = None) -> GitStatusResponse:
    ws = _resolve_workspace(root, workspace)
    try:
        branch = _run_git(ws, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except RuntimeError:
        branch = _run_git(ws, "symbolic-ref", "--short", "HEAD").strip()
    porcelain = _run_git(ws, "status", "--short")
    return GitStatusResponse(root=str(ws), branch=branch, porcelain=porcelain)


def git_diff(root: Path, workspace: str | None = None, *, cached: bool = False) -> GitDiffResponse:
    ws = _resolve_workspace(root, workspace)
    args = ["diff", "--no-ext-diff"]
    if cached:
        args.append("--cached")
    diff = _run_git(ws, *args)
    return GitDiffResponse(root=str(ws), diff=diff)


def git_diff_file(root: Path, path: str, workspace: str | None = None, *, cached: bool = False) -> GitDiffResponse:
    ws = _resolve_workspace(root, workspace)
    args = ["diff", "--no-ext-diff"]
    if cached:
        args.append("--cached")
    args.extend(["--", path])
    diff = _run_git(ws, *args)
    return GitDiffResponse(root=str(ws), diff=diff)


def git_changed_files(root: Path, workspace: str | None = None) -> GitChangedFilesResponse:
    ws = _resolve_workspace(root, workspace)
    output = _run_git(ws, "status", "--short")
    files = [line[3:] for line in output.splitlines() if len(line) >= 4]
    return GitChangedFilesResponse(root=str(ws), files=files)


def git_branch(root: Path, workspace: str | None = None) -> GitBranchResponse:
    ws = _resolve_workspace(root, workspace)
    try:
        branch = _run_git(ws, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except RuntimeError:
        branch = _run_git(ws, "symbolic-ref", "--short", "HEAD").strip()
    return GitBranchResponse(root=str(ws), branch=branch)


def git_log(root: Path, workspace: str | None = None, *, limit: int = 10) -> GitLogResponse:
    ws = _resolve_workspace(root, workspace)
    output = _run_git(
        ws,
        "log",
        f"-n{limit}",
        "--pretty=format:%H%x1f%an%x1f%ae%x1f%s",
    )
    entries: list[GitLogEntry] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        commit, author_name, author_email, subject = line.split("\x1f", 3)
        entries.append(
            GitLogEntry(
                commit=commit,
                author_name=author_name,
                author_email=author_email,
                subject=subject,
            )
        )
    return GitLogResponse(root=str(ws), entries=entries)


def git_show(root: Path, commit: str, workspace: str | None = None) -> GitShowResponse:
    ws = _resolve_workspace(root, workspace)
    patch = _run_git(ws, "show", "--no-ext-diff", "--stat=80", commit)
    return GitShowResponse(root=str(ws), commit=commit, patch=patch)
