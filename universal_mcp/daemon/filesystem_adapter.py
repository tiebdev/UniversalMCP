"""Internal filesystem adapter used as the first real MCP integration."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class FilesystemEntry(BaseModel):
    path: str
    name: str
    entry_type: str
    size: int | None = None


class FilesystemListResponse(BaseModel):
    root: str
    requested_path: str
    entries: list[FilesystemEntry] = Field(default_factory=list)


class FilesystemReadResponse(BaseModel):
    root: str
    requested_path: str
    content: str
    encoding: str = "utf-8"
    offset: int = 0
    bytes_read: int


class FilesystemExistsResponse(BaseModel):
    root: str
    requested_path: str
    exists: bool
    entry_type: Literal["file", "dir", "missing"]


class FilesystemStatResponse(BaseModel):
    root: str
    requested_path: str
    exists: bool
    entry_type: Literal["file", "dir", "missing"]
    size: int | None = None


class FilesystemMatch(BaseModel):
    path: str
    line: int
    column: int
    line_text: str


class FilesystemSearchResponse(BaseModel):
    root: str
    requested_path: str
    query: str
    matches: list[FilesystemMatch] = Field(default_factory=list)


class FilesystemGlobResponse(BaseModel):
    root: str
    pattern: str
    matches: list[FilesystemEntry] = Field(default_factory=list)


class FilesystemReadManyItem(BaseModel):
    path: str
    content: str
    bytes_read: int


class FilesystemReadManyResponse(BaseModel):
    root: str
    items: list[FilesystemReadManyItem] = Field(default_factory=list)


def _resolve_path(root: Path, requested_path: str) -> Path:
    candidate = (root / requested_path).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("Requested path escapes the workspace root")
    return candidate


def list_directory(root: Path, requested_path: str = ".") -> FilesystemListResponse:
    directory = _resolve_path(root, requested_path)
    if not directory.exists():
        raise FileNotFoundError(f"Path does not exist: {requested_path}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {requested_path}")

    entries: list[FilesystemEntry] = []
    for child in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
        stat = child.stat()
        entries.append(
            FilesystemEntry(
                path=str(child.relative_to(root.resolve())),
                name=child.name,
                entry_type="dir" if child.is_dir() else "file",
                size=None if child.is_dir() else stat.st_size,
            )
        )

    return FilesystemListResponse(
        root=str(root.resolve()),
        requested_path=requested_path,
        entries=entries,
    )


def read_file(root: Path, requested_path: str, *, offset: int = 0, max_bytes: int = 16 * 1024) -> FilesystemReadResponse:
    file_path = _resolve_path(root, requested_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Path does not exist: {requested_path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {requested_path}")

    with file_path.open("rb") as fh:
        fh.seek(offset)
        data = fh.read(max_bytes)

    return FilesystemReadResponse(
        root=str(root.resolve()),
        requested_path=requested_path,
        content=data.decode("utf-8", errors="replace"),
        offset=offset,
        bytes_read=len(data),
    )


def path_exists(root: Path, requested_path: str) -> FilesystemExistsResponse:
    path = _resolve_path(root, requested_path)
    if not path.exists():
        return FilesystemExistsResponse(
            root=str(root.resolve()),
            requested_path=requested_path,
            exists=False,
            entry_type="missing",
        )
    return FilesystemExistsResponse(
        root=str(root.resolve()),
        requested_path=requested_path,
        exists=True,
        entry_type="dir" if path.is_dir() else "file",
    )


def stat_path(root: Path, requested_path: str) -> FilesystemStatResponse:
    path = _resolve_path(root, requested_path)
    if not path.exists():
        return FilesystemStatResponse(
            root=str(root.resolve()),
            requested_path=requested_path,
            exists=False,
            entry_type="missing",
        )
    stat = path.stat()
    return FilesystemStatResponse(
        root=str(root.resolve()),
        requested_path=requested_path,
        exists=True,
        entry_type="dir" if path.is_dir() else "file",
        size=None if path.is_dir() else stat.st_size,
    )


def glob_paths(root: Path, pattern: str) -> FilesystemGlobResponse:
    root_resolved = root.resolve()
    matches: list[FilesystemEntry] = []
    for path in sorted(root_resolved.rglob("*"), key=lambda item: str(item.relative_to(root_resolved)).lower()):
        relative = str(path.relative_to(root_resolved))
        if not fnmatch(relative, pattern):
            continue
        stat = path.stat()
        matches.append(
            FilesystemEntry(
                path=relative,
                name=path.name,
                entry_type="dir" if path.is_dir() else "file",
                size=None if path.is_dir() else stat.st_size,
            )
        )
    return FilesystemGlobResponse(root=str(root_resolved), pattern=pattern, matches=matches)


def search_text(root: Path, requested_path: str, query: str, *, max_results: int = 50) -> FilesystemSearchResponse:
    search_root = _resolve_path(root, requested_path)
    if not search_root.exists():
        raise FileNotFoundError(f"Path does not exist: {requested_path}")

    files: list[Path]
    if search_root.is_file():
        files = [search_root]
    else:
        files = sorted(path for path in search_root.rglob("*") if path.is_file())

    matches: list[FilesystemMatch] = []
    root_resolved = root.resolve()
    for file_path in files:
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            col = line.find(query)
            if col == -1:
                continue
            matches.append(
                FilesystemMatch(
                    path=str(file_path.relative_to(root_resolved)),
                    line=line_no,
                    column=col + 1,
                    line_text=line,
                )
            )
            if len(matches) >= max_results:
                return FilesystemSearchResponse(
                    root=str(root_resolved),
                    requested_path=requested_path,
                    query=query,
                    matches=matches,
                )

    return FilesystemSearchResponse(
        root=str(root_resolved),
        requested_path=requested_path,
        query=query,
        matches=matches,
    )


def read_many(root: Path, paths: list[str], *, max_bytes_each: int = 8 * 1024) -> FilesystemReadManyResponse:
    items: list[FilesystemReadManyItem] = []
    for requested_path in paths:
        file_response = read_file(root, requested_path, max_bytes=max_bytes_each)
        items.append(
            FilesystemReadManyItem(
                path=requested_path,
                content=file_response.content,
                bytes_read=file_response.bytes_read,
            )
        )
    return FilesystemReadManyResponse(root=str(root.resolve()), items=items)
