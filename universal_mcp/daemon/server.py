"""Background daemon process entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException

from universal_mcp.config.catalog import CatalogEntry, filter_catalog, load_default_catalog, split_catalog
from universal_mcp.config.profiles import ProfileConfig, ServiceConfig
from universal_mcp.config.secrets import get_secret
from universal_mcp.config.settings import load_settings
from universal_mcp.daemon.filesystem_adapter import list_directory, read_file
from universal_mcp.daemon.filesystem_adapter import glob_paths, path_exists, read_many, search_text, stat_path
from universal_mcp.daemon.git_adapter import (
    git_branch,
    git_changed_files,
    git_diff,
    git_diff_file,
    git_log,
    git_show,
    git_status,
)
from universal_mcp.daemon.internal_tools import build_internal_tool_executor
from universal_mcp.daemon.memory_filter import apply_response_policy
from universal_mcp.daemon.multiplexer import create_app
from universal_mcp.daemon.process_router import ProcessRouter
from universal_mcp.daemon.state import DaemonStatus, ExternalMcpPreflight, ManagedProcessStatus, ProcessState
from universal_mcp.daemon.translator import translate_payload
from universal_mcp.observability.events import EventRecord
from universal_mcp.observability.logging import append_event
from universal_mcp.runtime.pid import clear_pid, write_pid
from universal_mcp.runtime.state_store import clear_state, write_state


def _settings_path(root: Path) -> Path:
    return root / ".universal_mcp.json"


def build_status(default_profile: str, port: int, router: ProcessRouter) -> DaemonStatus:
    return DaemonStatus(
        port=port,
        default_profile=default_profile,
        processes=router.list_statuses(),
    )


def _resolve_secret(secret_ref: str | None, root: Path | None = None) -> str | None:
    if not secret_ref:
        return None
    names = [
        f"UNIVERSAL_MCP_SECRET_{secret_ref.upper()}",
        secret_ref.upper(),
    ]
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return get_secret(secret_ref, root=root)


def _service_env(name: str, service: ServiceConfig | None, root: Path | None = None) -> dict[str, str]:
    if service is None:
        return {}

    env: dict[str, str] = {}
    if name == "github":
        if service.host:
            env["GITHUB_API_URL"] = service.host
        resolved_secret = _resolve_secret(service.secret_ref, root=root)
        if resolved_secret:
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = resolved_secret
        return env

    if name == "postgres":
        if service.host:
            env["PG_HOST"] = service.host
        if service.port is not None:
            env["PG_PORT"] = str(service.port)
        if service.database:
            env["PG_DATABASE"] = service.database
        if service.user:
            env["PG_USER"] = service.user
        resolved_secret = _resolve_secret(service.secret_ref, root=root)
        if resolved_secret:
            env["PG_PASSWORD"] = resolved_secret
        return env

    prefix = name.upper().replace("-", "_")
    if service.host:
        env[f"{prefix}_HOST"] = service.host
    if service.port is not None:
        env[f"{prefix}_PORT"] = str(service.port)
    if service.database:
        env[f"{prefix}_DATABASE"] = service.database
    if service.user:
        env[f"{prefix}_USER"] = service.user
    resolved_secret = _resolve_secret(service.secret_ref, root=root)
    if resolved_secret:
        env[f"{prefix}_SECRET"] = resolved_secret
    return env


def _env_by_name(
    profile: ProfileConfig | None,
    enabled_names: list[str],
    root: Path | None = None,
) -> dict[str, dict[str, str]]:
    if profile is None:
        return {}
    return {name: _service_env(name, profile.services.get(name), root=root) for name in enabled_names}


def _preflight_errors_by_name(
    profile: ProfileConfig | None,
    enabled_catalog,
    root: Path | None = None,
) -> dict[str, list[str]]:
    if profile is None:
        return {}

    errors: dict[str, list[str]] = {}
    for entry in enabled_catalog:
        entry_errors: list[str] = []
        service = profile.services.get(entry.name)
        env = _service_env(entry.name, service, root=root)
        for secret in entry.required_secrets:
            if secret == "github_token" and "GITHUB_PERSONAL_ACCESS_TOKEN" not in env:
                entry_errors.append("Missing required secret: github_token")
            elif secret == "postgres_password" and "PG_PASSWORD" not in env:
                entry_errors.append("Missing required secret: postgres_password")
        if entry.name == "postgres":
            required_env_keys = {
                "PG_HOST": "Missing required setting: postgres.host",
                "PG_PORT": "Missing required setting: postgres.port",
                "PG_USER": "Missing required setting: postgres.user",
                "PG_DATABASE": "Missing required setting: postgres.database",
            }
            for env_key, message in required_env_keys.items():
                if env_key not in env:
                    entry_errors.append(message)
        if entry.name == "ast-grep" and shutil.which("ast-grep") is None:
            entry_errors.append("Missing required command: ast-grep")
        errors[entry.name] = entry_errors
    return errors


def _build_external_preflight(
    *,
    name: str,
    enabled_names: list[str],
    external_catalog_by_name: dict[str, CatalogEntry],
    env_by_name: dict[str, dict[str, str]],
    preflight_errors_by_name: dict[str, list[str]],
    router: ProcessRouter,
) -> ExternalMcpPreflight:
    entry = external_catalog_by_name[name]
    env = env_by_name.get(name, {})
    errors = preflight_errors_by_name.get(name, [])
    process_state = None
    if name in router.managed_names():
        process_state = router.get_status(name).state
    return ExternalMcpPreflight(
        name=name,
        enabled=name in enabled_names,
        executable_available=shutil.which(entry.command) is not None,
        required_env_present=not errors,
        env_keys=sorted(env.keys()),
        missing_requirements=errors,
        process_state=process_state,
    )


def _external_error_detail(name: str, action: str, request_id: str, exc: Exception) -> dict[str, str]:
    return {
        "request_id": request_id,
        "mcp_name": name,
        "action": action,
        "error": str(exc),
    }


def create_filesystem_handlers(root: Path, log_event):
    execute = build_internal_tool_executor(root, log_event)

    async def filesystem_list_handler(path: str, workspace: str | None):
        return await execute(
            tool_name="filesystem",
            event_name="filesystem_list",
            message=f"listed {path}",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: list_directory(workspace_root, path),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "requested_path": response.requested_path,
                    "entries": [entry.model_dump(mode="json") for entry in response.entries],
                },
                [entry.model_dump(mode="json") for entry in response.entries],
            ),
        )

    async def filesystem_read_handler(path: str, workspace: str | None, offset: int, max_bytes: int):
        return await execute(
            tool_name="filesystem",
            event_name="filesystem_read",
            message=f"read {path}",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: read_file(
                workspace_root,
                path,
                offset=offset,
                max_bytes=max_bytes,
            ),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "requested_path": response.requested_path,
                    "offset": response.offset,
                    "bytes_read": response.bytes_read,
                    "content": response.content,
                },
                response.content,
            ),
            filtered_field="content",
        )

    async def filesystem_exists_handler(path: str, workspace: str | None):
        return await execute(
            tool_name="filesystem",
            event_name="filesystem_exists",
            message=f"checked {path}",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: path_exists(workspace_root, path),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "requested_path": response.requested_path,
                    "exists": response.exists,
                    "entry_type": response.entry_type,
                },
                response.model_dump(mode="json"),
            ),
        )

    async def filesystem_stat_handler(path: str, workspace: str | None):
        return await execute(
            tool_name="filesystem",
            event_name="filesystem_stat",
            message=f"statted {path}",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: stat_path(workspace_root, path),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    **response.model_dump(mode="json"),
                },
                response.model_dump(mode="json"),
            ),
        )

    async def filesystem_glob_handler(pattern: str, workspace: str | None):
        return await execute(
            tool_name="filesystem",
            event_name="filesystem_glob",
            message=f"globbed {pattern}",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: glob_paths(workspace_root, pattern),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "pattern": response.pattern,
                    "matches": [entry.model_dump(mode="json") for entry in response.matches],
                },
                [entry.model_dump(mode="json") for entry in response.matches],
            ),
            filtered_field="matches",
        )

    async def filesystem_search_handler(
        path: str,
        workspace: str | None,
        query: str,
        max_results: int,
    ):
        return await execute(
            tool_name="filesystem",
            event_name="filesystem_search_text",
            message=f"searched {path} for text",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: search_text(
                workspace_root,
                path,
                query,
                max_results=max_results,
            ),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "requested_path": response.requested_path,
                    "query": response.query,
                    "matches": [match.model_dump(mode="json") for match in response.matches],
                },
                [match.model_dump(mode="json") for match in response.matches],
            ),
            filtered_field="matches",
        )

    async def filesystem_read_many_handler(paths: list[str], workspace: str | None, max_bytes_each: int):
        return await execute(
            tool_name="filesystem",
            event_name="filesystem_read_many",
            message=f"read {len(paths)} files",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: read_many(workspace_root, paths, max_bytes_each=max_bytes_each),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "items": [item.model_dump(mode="json") for item in response.items],
                },
                [item.model_dump(mode="json") for item in response.items],
            ),
            filtered_field="items",
        )

    return (
        filesystem_list_handler,
        filesystem_read_handler,
        filesystem_exists_handler,
        filesystem_stat_handler,
        filesystem_glob_handler,
        filesystem_search_handler,
        filesystem_read_many_handler,
    )


def create_git_handlers(root: Path, log_event):
    execute = build_internal_tool_executor(root, log_event)

    async def git_status_handler(workspace: str | None):
        return await execute(
            tool_name="git",
            event_name="git_status",
            message="git status requested",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: git_status(workspace_root),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "branch": response.branch,
                    "porcelain": response.porcelain,
                },
                response.porcelain,
            ),
        )

    async def git_diff_handler(workspace: str | None, cached: bool):
        return await execute(
            tool_name="git",
            event_name="git_diff",
            message="git diff requested",
            workspace=workspace,
            kind="diff",
            operation=lambda workspace_root: git_diff(workspace_root, cached=cached),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "diff": response.diff,
                },
                response.diff,
            ),
            filtered_field="diff",
        )

    async def git_changed_files_handler(workspace: str | None):
        return await execute(
            tool_name="git",
            event_name="git_changed_files",
            message="git changed files requested",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: git_changed_files(workspace_root),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "files": response.files,
                },
                response.files,
            ),
            filtered_field="files",
        )

    async def git_branch_handler(workspace: str | None):
        return await execute(
            tool_name="git",
            event_name="git_branch",
            message="git branch requested",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: git_branch(workspace_root),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "branch": response.branch,
                },
                response.model_dump(mode="json"),
            ),
        )

    async def git_log_handler(workspace: str | None, limit: int):
        return await execute(
            tool_name="git",
            event_name="git_log",
            message=f"git log requested ({limit})",
            workspace=workspace,
            kind="generic",
            operation=lambda workspace_root: git_log(workspace_root, limit=limit),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "entries": [entry.model_dump(mode="json") for entry in response.entries],
                },
                [entry.model_dump(mode="json") for entry in response.entries],
            ),
            filtered_field="entries",
        )

    async def git_show_handler(workspace: str | None, commit: str):
        return await execute(
            tool_name="git",
            event_name="git_show",
            message=f"git show requested for {commit}",
            workspace=workspace,
            kind="diff",
            operation=lambda workspace_root: git_show(workspace_root, commit),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "commit": response.commit,
                    "patch": response.patch,
                },
                response.patch,
            ),
            filtered_field="patch",
        )

    async def git_diff_file_handler(workspace: str | None, path: str, cached: bool):
        return await execute(
            tool_name="git",
            event_name="git_diff_file",
            message=f"git diff file requested for {path}",
            workspace=workspace,
            kind="diff",
            operation=lambda workspace_root: git_diff_file(workspace_root, path, cached=cached),
            response_builder=lambda response, request_id: (
                {
                    "request_id": request_id,
                    "root": response.root,
                    "path": path,
                    "diff": response.diff,
                },
                response.diff,
            ),
            filtered_field="diff",
        )

    return (
        git_status_handler,
        git_diff_handler,
        git_changed_files_handler,
        git_branch_handler,
        git_log_handler,
        git_show_handler,
        git_diff_file_handler,
    )


def build_internal_statuses(internal_catalog) -> dict[str, ManagedProcessStatus]:
    return {
        entry.name: ManagedProcessStatus(name=entry.name, state=ProcessState.HEALTHY)
        for entry in internal_catalog
    }


def create_daemon_app(*, default_profile: str, port: int, root: Path) -> FastAPI:
    settings = load_settings(_settings_path(root))
    profile = settings.profiles.get(default_profile)
    enabled_names = profile.enabled_mcps if profile else []
    enabled_catalog = filter_catalog(load_default_catalog(), enabled_names)
    internal_catalog, external_catalog = split_catalog(enabled_catalog)
    external_catalog_by_name = {entry.name: entry for entry in external_catalog}
    env_by_name = _env_by_name(profile, enabled_names, root=root)
    preflight_errors_by_name = _preflight_errors_by_name(profile, external_catalog, root=root)
    router = ProcessRouter(
        external_catalog,
        env_by_name=env_by_name,
        preflight_errors_by_name=preflight_errors_by_name,
    )
    status = build_status(default_profile=default_profile, port=port, router=router)
    internal_statuses = build_internal_statuses(internal_catalog)
    previous_states: dict[str, str] = {}

    def log_event(**kwargs) -> None:
        append_event(EventRecord(profile=default_profile, **kwargs), root=root)
    (
        filesystem_list_handler,
        filesystem_read_handler,
        filesystem_exists_handler,
        filesystem_stat_handler,
        filesystem_glob_handler,
        filesystem_search_handler,
        filesystem_read_many_handler,
    ) = create_filesystem_handlers(root, log_event)
    (
        git_status_handler,
        git_diff_handler,
        git_changed_files_handler,
        git_branch_handler,
        git_log_handler,
        git_show_handler,
        git_diff_file_handler,
    ) = create_git_handlers(root, log_event)

    async def sync_status() -> DaemonStatus:
        external_statuses = {process.name: process for process in await router.snapshot()}
        merged: list[ManagedProcessStatus] = []
        for name, process in {**internal_statuses, **external_statuses}.items():
            merged.append(process)
        status.processes = merged
        for process in status.processes:
            previous = previous_states.get(process.name)
            current = process.state.value
            if previous != current:
                log_event(
                    level="info",
                    component="daemon",
                    event="process_state_changed",
                    message=f"{process.name} -> {current}",
                    mcp_name=process.name,
                    process_state=current,
                )
                previous_states[process.name] = current
        write_state(status, root=root)
        return status

    async def preview_handler(request: dict) -> dict:
        request_id = str(uuid.uuid4())
        translated = translate_payload(
            request["payload"],
            target_client=request.get("target_client", "codex-cli"),
        )
        filtered_payload, metadata = apply_response_policy(
            translated.payload,
            kind=request.get("kind", "generic"),
            cursor=request.get("cursor"),
        )
        log_event(
            level="info",
            component="multiplexer",
            event="tool_preview",
            message="tool preview processed",
            request_id=request_id,
        )
        return {
            "request_id": request_id,
            "translated": translated.model_dump(mode="json"),
            "filtered_payload": filtered_payload,
            "filter_metadata": {
                "truncated": metadata.truncated,
                "original_size_estimate": metadata.original_size_estimate,
                "returned_size": metadata.returned_size,
                "policy_applied": metadata.policy_applied,
                "next_cursor": metadata.next_cursor,
            },
        }

    async def process_list_handler():
        await sync_status()
        return status.processes

    async def process_restart_handler(name: str):
        if name in internal_statuses:
            result = internal_statuses[name]
            log_event(
                level="info",
                component="daemon",
                event="process_restarted",
                message=f"{name} restart requested (internal no-op)",
                mcp_name=name,
                process_state=result.state.value,
            )
            return result
        result = await router.restart_process(name)
        await sync_status()
        log_event(
            level="info",
            component="daemon",
            event="process_restarted",
            message=f"{name} restart requested",
            mcp_name=name,
            process_state=result.state.value,
        )
        return result

    async def external_tools_list_handler(name: str, cursor: str | None):
        request_id = str(uuid.uuid4())
        try:
            result = await router.list_tools(name, cursor)
        except Exception as exc:
            log_event(
                level="error",
                component="external",
                event="external_tools_list_failed",
                message=f"failed to list tools for {name}",
                request_id=request_id,
                mcp_name=name,
            )
            raise HTTPException(
                status_code=502,
                detail=_external_error_detail(name, "tools/list", request_id, exc),
            ) from exc
        tools = result.get("tools", [])
        filtered_tools, metadata = apply_response_policy(tools, kind="generic", cursor=cursor)
        log_event(
            level="info",
            component="external",
            event="external_tools_list",
            message=f"listed tools for {name}",
            request_id=request_id,
            mcp_name=name,
        )
        return {
            "request_id": request_id,
            "mcp_name": name,
            "tools": filtered_tools,
            "next_cursor": result.get("nextCursor"),
            "filter_metadata": {
                "truncated": metadata.truncated,
                "original_size_estimate": metadata.original_size_estimate,
                "returned_size": metadata.returned_size,
                "policy_applied": metadata.policy_applied,
                "next_cursor": metadata.next_cursor,
            },
        }

    async def external_tool_call_handler(name: str, tool_name: str, arguments: dict | None):
        request_id = str(uuid.uuid4())
        try:
            result = await router.call_tool(name, tool_name, arguments)
        except Exception as exc:
            log_event(
                level="error",
                component="external",
                event="external_tool_call_failed",
                message=f"failed to call tool {tool_name} on {name}",
                request_id=request_id,
                mcp_name=name,
            )
            raise HTTPException(
                status_code=502,
                detail=_external_error_detail(name, f"tools/call:{tool_name}", request_id, exc),
            ) from exc
        filtered_result, metadata = apply_response_policy(result, kind="generic")
        log_event(
            level="info",
            component="external",
            event="external_tool_call",
            message=f"called tool {tool_name} on {name}",
            request_id=request_id,
            mcp_name=name,
        )
        return {
            "request_id": request_id,
            "mcp_name": name,
            "tool_name": tool_name,
            "result": filtered_result,
            "filter_metadata": {
                "truncated": metadata.truncated,
                "original_size_estimate": metadata.original_size_estimate,
                "returned_size": metadata.returned_size,
                "policy_applied": metadata.policy_applied,
                "next_cursor": metadata.next_cursor,
            },
        }

    async def external_preflight_handler(name: str) -> ExternalMcpPreflight:
        return _build_external_preflight(
            name=name,
            enabled_names=enabled_names,
            external_catalog_by_name=external_catalog_by_name,
            env_by_name=env_by_name,
            preflight_errors_by_name=preflight_errors_by_name,
            router=router,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        stop_event = asyncio.Event()

        async def sync_loop() -> None:
            while not stop_event.is_set():
                await sync_status()
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

        write_pid(os.getpid(), root=root)
        log_event(
            level="info",
            component="daemon",
            event="daemon_started",
            message=f"daemon started on port {port}",
        )
        await router.start_all()
        await sync_status()
        task = asyncio.create_task(sync_loop())
        yield
        stop_event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await router.stop_all()
        log_event(
            level="info",
            component="daemon",
            event="daemon_stopped",
            message="daemon stopped",
        )
        clear_pid(root=root)
        clear_state(root=root)

    app = create_app(
        sync_status,
        preview_handler,
        process_list_handler,
        process_restart_handler,
        filesystem_list_handler,
        filesystem_read_handler,
        filesystem_exists_handler,
        filesystem_stat_handler,
        filesystem_glob_handler,
        filesystem_search_handler,
        filesystem_read_many_handler,
        git_status_handler,
        git_diff_handler,
        git_changed_files_handler,
        git_branch_handler,
        git_log_handler,
        git_show_handler,
        git_diff_file_handler,
        external_preflight_handler,
        external_tools_list_handler,
        external_tool_call_handler,
    )
    app.router.lifespan_context = lifespan
    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--default-profile", required=True)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    app = create_daemon_app(
        default_profile=args.default_profile,
        port=args.port,
        root=Path(args.root),
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
