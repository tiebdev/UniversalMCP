"""HTTP + SSE daemon entrypoint."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from universal_mcp.daemon.state import DaemonStatus, ExternalMcpPreflight, ManagedProcessStatus

StatusProvider = Callable[[], Awaitable[DaemonStatus]]
PreviewHandler = Callable[[dict], Awaitable[dict]]
ProcessListHandler = Callable[[], Awaitable[list[ManagedProcessStatus]]]
ProcessActionHandler = Callable[[str], Awaitable[ManagedProcessStatus]]
FilesystemListHandler = Callable[[str, str | None], Awaitable[dict]]
FilesystemReadHandler = Callable[[str, str, int, int], Awaitable[dict]]
FilesystemExistsHandler = Callable[[str, str | None], Awaitable[dict]]
FilesystemStatHandler = Callable[[str, str | None], Awaitable[dict]]
FilesystemGlobHandler = Callable[[str, str | None], Awaitable[dict]]
FilesystemSearchHandler = Callable[[str, str | None, str, int], Awaitable[dict]]
FilesystemReadManyHandler = Callable[[list[str], str | None, int], Awaitable[dict]]
GitStatusHandler = Callable[[str | None], Awaitable[dict]]
GitDiffHandler = Callable[[str | None, bool], Awaitable[dict]]
GitChangedFilesHandler = Callable[[str | None], Awaitable[dict]]
GitBranchHandler = Callable[[str | None], Awaitable[dict]]
GitLogHandler = Callable[[str | None, int], Awaitable[dict]]
GitShowHandler = Callable[[str | None, str], Awaitable[dict]]
GitDiffFileHandler = Callable[[str | None, str, bool], Awaitable[dict]]
ExternalPreflightHandler = Callable[[str], Awaitable[ExternalMcpPreflight]]
ExternalToolsListHandler = Callable[[str, str | None], Awaitable[dict]]
ExternalToolCallHandler = Callable[[str, str, dict | None], Awaitable[dict]]


class PreviewRequest(BaseModel):
    payload: dict
    target_client: str = "codex-cli"
    kind: str = "generic"
    cursor: str | None = None


class FilesystemReadRequest(BaseModel):
    path: str
    workspace: str | None = None
    offset: int = 0
    max_bytes: int = 16 * 1024


class FilesystemSearchRequest(BaseModel):
    path: str = "."
    workspace: str | None = None
    query: str
    max_results: int = 50


class FilesystemReadManyRequest(BaseModel):
    paths: list[str]
    workspace: str | None = None
    max_bytes_each: int = 8 * 1024


class GitDiffRequest(BaseModel):
    workspace: str | None = None
    cached: bool = False


class GitLogRequest(BaseModel):
    workspace: str | None = None
    limit: int = 10


class GitShowRequest(BaseModel):
    workspace: str | None = None
    commit: str


class GitDiffFileRequest(BaseModel):
    workspace: str | None = None
    path: str
    cached: bool = False


class ExternalToolCallRequest(BaseModel):
    arguments: dict | None = None


def create_app(
    status_provider: StatusProvider,
    preview_handler: PreviewHandler,
    process_list_handler: ProcessListHandler,
    process_restart_handler: ProcessActionHandler,
    filesystem_list_handler: FilesystemListHandler,
    filesystem_read_handler: FilesystemReadHandler,
    filesystem_exists_handler: FilesystemExistsHandler,
    filesystem_stat_handler: FilesystemStatHandler,
    filesystem_glob_handler: FilesystemGlobHandler,
    filesystem_search_handler: FilesystemSearchHandler,
    filesystem_read_many_handler: FilesystemReadManyHandler,
    git_status_handler: GitStatusHandler,
    git_diff_handler: GitDiffHandler,
    git_changed_files_handler: GitChangedFilesHandler,
    git_branch_handler: GitBranchHandler,
    git_log_handler: GitLogHandler,
    git_show_handler: GitShowHandler,
    git_diff_file_handler: GitDiffFileHandler,
    external_preflight_handler: ExternalPreflightHandler,
    external_tools_list_handler: ExternalToolsListHandler,
    external_tool_call_handler: ExternalToolCallHandler,
) -> FastAPI:
    app = FastAPI(title="Universal MCP Orchestrator", version="0.1.0")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status", response_model=DaemonStatus)
    async def get_status() -> DaemonStatus:
        return await status_provider()

    @app.get("/events")
    async def events() -> StreamingResponse:
        async def event_stream():
            while True:
                status = await status_provider()
                payload = json.dumps(status.model_dump(mode="json"))
                yield f"event: status\ndata: {payload}\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/tool-preview")
    async def tool_preview(request: PreviewRequest) -> dict:
        return await preview_handler(request.model_dump())

    @app.get("/mcps", response_model=list[ManagedProcessStatus])
    async def list_mcps() -> list[ManagedProcessStatus]:
        return await process_list_handler()

    @app.post("/mcps/{name}/restart", response_model=ManagedProcessStatus)
    async def restart_mcp(name: str) -> ManagedProcessStatus:
        return await process_restart_handler(name)

    @app.get("/filesystem/list")
    async def filesystem_list(path: str = ".", workspace: str | None = None) -> dict:
        return await filesystem_list_handler(path, workspace)

    @app.post("/filesystem/read")
    async def filesystem_read(request: FilesystemReadRequest) -> dict:
        return await filesystem_read_handler(
            request.path,
            request.workspace,
            request.offset,
            request.max_bytes,
        )

    @app.get("/filesystem/exists")
    async def filesystem_exists(path: str, workspace: str | None = None) -> dict:
        return await filesystem_exists_handler(path, workspace)

    @app.get("/filesystem/stat")
    async def filesystem_stat(path: str, workspace: str | None = None) -> dict:
        return await filesystem_stat_handler(path, workspace)

    @app.get("/filesystem/glob")
    async def filesystem_glob(pattern: str, workspace: str | None = None) -> dict:
        return await filesystem_glob_handler(pattern, workspace)

    @app.post("/filesystem/search-text")
    async def filesystem_search_text(request: FilesystemSearchRequest) -> dict:
        return await filesystem_search_handler(
            request.path,
            request.workspace,
            request.query,
            request.max_results,
        )

    @app.post("/filesystem/read-many")
    async def filesystem_read_many(request: FilesystemReadManyRequest) -> dict:
        return await filesystem_read_many_handler(
            request.paths,
            request.workspace,
            request.max_bytes_each,
        )

    @app.get("/git/status")
    async def git_status(workspace: str | None = None) -> dict:
        return await git_status_handler(workspace)

    @app.post("/git/diff")
    async def git_diff(request: GitDiffRequest) -> dict:
        return await git_diff_handler(request.workspace, request.cached)

    @app.get("/git/changed-files")
    async def git_changed_files(workspace: str | None = None) -> dict:
        return await git_changed_files_handler(workspace)

    @app.get("/git/branch")
    async def git_branch(workspace: str | None = None) -> dict:
        return await git_branch_handler(workspace)

    @app.post("/git/log")
    async def git_log(request: GitLogRequest) -> dict:
        return await git_log_handler(request.workspace, request.limit)

    @app.post("/git/show")
    async def git_show(request: GitShowRequest) -> dict:
        return await git_show_handler(request.workspace, request.commit)

    @app.post("/git/diff-file")
    async def git_diff_file(request: GitDiffFileRequest) -> dict:
        return await git_diff_file_handler(request.workspace, request.path, request.cached)

    @app.get("/external/{name}/preflight", response_model=ExternalMcpPreflight)
    async def external_preflight(name: str) -> ExternalMcpPreflight:
        try:
            return await external_preflight_handler(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown external MCP: {name}") from exc

    @app.get("/github/preflight", response_model=ExternalMcpPreflight)
    async def github_preflight() -> ExternalMcpPreflight:
        return await external_preflight_handler("github")

    @app.get("/postgres/preflight", response_model=ExternalMcpPreflight)
    async def postgres_preflight() -> ExternalMcpPreflight:
        return await external_preflight_handler("postgres")

    @app.get("/external/{name}/tools")
    async def external_tools(name: str, cursor: str | None = None) -> dict:
        return await external_tools_list_handler(name, cursor)

    @app.post("/external/{name}/tools/{tool_name}")
    async def external_tool_call(name: str, tool_name: str, request: ExternalToolCallRequest) -> dict:
        return await external_tool_call_handler(name, tool_name, request.arguments)

    return app
