"""Typer CLI entrypoint."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
import typer

from universal_mcp.cli.onboarding import (
    bootstrap_settings,
    build_pending_items,
    build_preflight_checks,
    configured_service_names,
    onboarding_summary,
    registered_secret_refs,
    run_guided_onboarding,
)
from universal_mcp.cli.views import (
    build_catalog_table,
    build_doctor_table,
    build_onboarding_intro,
    build_run_context_table,
    build_onboarding_summary_panel,
    build_preflight_table,
    build_profile_services_table,
    build_profile_table,
    build_secrets_table,
    build_status_table,
)
from universal_mcp.config.catalog import catalog_names, load_default_catalog
from universal_mcp.config.profiles import ProfileConfig, ServiceConfig, WorkspacePolicy
from universal_mcp.config.secrets import delete_secret, list_secret_records, secret_backend_name, set_secret
from universal_mcp.config.settings import Settings, default_settings_path, ensure_settings, load_settings, save_settings
from universal_mcp.cli.wrapper import (
    WrapperValidationError,
    build_wrapper_context,
    run_wrapped_command,
)
from universal_mcp.daemon.process_router import ProcessRouter
from universal_mcp.daemon.state import DaemonStatus
from universal_mcp.observability.logging import read_events
from universal_mcp.runtime.daemon_control import (
    describe_daemon,
    last_known_status,
    start_daemon,
    stop_daemon,
)

app = typer.Typer(help="Universal MCP Orchestrator CLI")
profile_app = typer.Typer(help="Profile management commands")
service_app = typer.Typer(help="Profile service configuration commands")
secret_app = typer.Typer(help="Secret management commands")
app.add_typer(profile_app, name="profile")
profile_app.add_typer(service_app, name="service")
app.add_typer(secret_app, name="secret")

console = Console()


def _settings_and_profile(path: Path, profile_name: str):
    settings = ensure_settings(path)
    if profile_name not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {profile_name}")
    return settings, settings.profiles[profile_name]


def _validate_mcps(mcp_names: list[str]) -> list[str]:
    known = set(catalog_names())
    invalid = [name for name in mcp_names if name not in known]
    if invalid:
        raise typer.BadParameter(f"MCP desconocido: {', '.join(invalid)}")
    return mcp_names


def _secret_usage_by_ref(settings: Settings) -> dict[str, list[str]]:
    usage: dict[str, list[str]] = {}
    for profile_name, profile in settings.profiles.items():
        for service_name, service in profile.services.items():
            if not service.secret_ref:
                continue
            usage.setdefault(service.secret_ref, []).append(f"{profile_name}.{service_name}")
    return {ref: sorted(locations) for ref, locations in usage.items()}


def _secret_usage_for_ref(ref: str, settings: Settings) -> list[str]:
    return _secret_usage_by_ref(settings).get(ref, [])


def _resolve_run_workspace(profile: ProfileConfig, workspace: Path | None) -> Path:
    if workspace is not None:
        return workspace.resolve()

    if profile.workspace_policy.mode == "fixed":
        if not profile.workspace_policy.path:
            raise typer.BadParameter(
                "El perfil usa workspace_policy=fixed pero no tiene una ruta configurada"
            )
        fixed_path = Path(profile.workspace_policy.path).expanduser().resolve()
        if not fixed_path.exists():
            raise typer.BadParameter(f"El workspace fijo no existe: {fixed_path}")
        return fixed_path

    return Path.cwd().resolve()


def _build_status() -> DaemonStatus:
    settings = ensure_settings(default_settings_path())
    persisted = last_known_status()
    if persisted:
        return persisted
    router = ProcessRouter(load_default_catalog())
    return DaemonStatus(
        port=settings.runtime.port,
        default_profile=settings.default_profile,
        processes=router.list_statuses(),
    )


@app.command()
def start() -> None:
    settings = ensure_settings(default_settings_path())
    started, message = start_daemon(settings)
    console.print(message)
    if not started and "ya operativo" not in message:
        raise typer.Exit(code=1)


@app.command()
def stop() -> None:
    settings = ensure_settings(default_settings_path())
    stopped, message = stop_daemon(settings.runtime.port)
    console.print(message)
    if not stopped:
        raise typer.Exit(code=1)


@app.command()
def restart() -> None:
    settings = ensure_settings(default_settings_path())
    _, stop_message = stop_daemon(settings.runtime.port)
    console.print(stop_message)
    started, start_message = start_daemon(settings)
    console.print(start_message)
    if not started:
        raise typer.Exit(code=1)


@app.command()
def status() -> None:
    settings = ensure_settings(default_settings_path())
    is_running, message, pid = describe_daemon(settings)
    daemon_status = _build_status()
    console.print(message)
    console.print(f"PID: {pid or '-'}")
    console.print(f"Puerto: {daemon_status.port}")
    console.print(f"Perfil por defecto: {daemon_status.default_profile or '-'}")
    console.print(build_status_table(daemon_status))
    if not is_running:
        raise typer.Exit(code=1)


@app.command()
def config() -> None:
    settings = ensure_settings(default_settings_path())
    console.print(settings.model_dump_json(indent=2))


@app.command()
def catalog() -> None:
    console.print(build_catalog_table(load_default_catalog()))


@app.command()
def doctor() -> None:
    settings = ensure_settings(default_settings_path())
    console.print(build_doctor_table(settings, load_default_catalog()))


@secret_app.command("list")
def list_secrets() -> None:
    path = default_settings_path()
    settings = load_settings(path)
    console.print(build_secrets_table(list_secret_records(), _secret_usage_by_ref(settings)))


@secret_app.command("set")
def set_secret_command(
    ref: str,
    value: str | None = typer.Argument(None),
) -> None:
    secret_value = value or typer.prompt("Valor del secreto", hide_input=True, confirmation_prompt=True)
    record = set_secret(ref, secret_value)
    console.print(f"Secreto actualizado: {record.ref} ({record.backend})")


@secret_app.command("rotate")
def rotate_secret_command(
    ref: str,
    value: str | None = typer.Argument(None),
) -> None:
    path = default_settings_path()
    settings = load_settings(path)
    usage = _secret_usage_for_ref(ref, settings)
    if usage:
        console.print(f"Referencias activas para {ref}: {', '.join(usage)}")
    else:
        console.print(f"Sin referencias activas para {ref}. Se creará o actualizará igualmente.")

    secret_value = value or typer.prompt("Nuevo valor del secreto", hide_input=True, confirmation_prompt=True)
    record = set_secret(ref, secret_value)
    console.print(f"Secreto rotado: {record.ref} ({record.backend})")


@secret_app.command("delete")
def delete_secret_command(ref: str) -> None:
    removed = delete_secret(ref)
    if not removed:
        console.print(f"Secreto no encontrado: {ref}")
        raise typer.Exit(code=1)
    console.print(f"Secreto eliminado: {ref}")


@app.command()
def logs(
    level: str | None = typer.Option(None, help="Filter by event level"),
    mcp: str | None = typer.Option(None, "--mcp", help="Filter by MCP name"),
) -> None:
    events = read_events(level=level, mcp_name=mcp)
    if not events:
        console.print("No hay eventos registrados.")
        return

    for event in events:
        console.print(
            f"[{event.timestamp.isoformat()}] {event.level} {event.component}:{event.event} "
            f"{event.message}"
        )


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
    command: list[str] = typer.Argument(..., help="External client command"),
    profile: str | None = typer.Option(None, help="Profile to use"),
    workspace: Path | None = typer.Option(None, help="Workspace path to inject"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate and render the launch context without executing the client",
    ),
    ensure_daemon_running: bool = typer.Option(
        True,
        "--ensure-daemon/--no-ensure-daemon",
        help="Start daemon if needed before launching the client",
    ),
) -> None:
    command = [*command, *ctx.args]

    path = default_settings_path()
    settings = ensure_settings(path)
    profile_name = profile or settings.default_profile
    if profile_name not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {profile_name}")
    profile = settings.profiles[profile_name]

    target_workspace = _resolve_run_workspace(profile, workspace)
    try:
        plan, extra_env = build_wrapper_context(
            settings=settings,
            profile_name=profile_name,
            profile=profile,
            command=command,
            workspace=target_workspace,
        )
    except WrapperValidationError as exc:
        console.print(str(exc))
        raise typer.Exit(code=1) from exc

    console.print(
        build_run_context_table(
            profile_name=profile_name,
            target_client=plan.display_name,
            executable=plan.resolved_executable or plan.executable,
            workspace=str(target_workspace),
            daemon_url=extra_env["UNIVERSAL_MCP_DAEMON_URL"],
            ensure_daemon_running=ensure_daemon_running,
            dry_run=dry_run,
        )
    )
    console.print(plan.launch_message)
    for warning in plan.warnings:
        console.print(f"WARN: {warning}")

    if dry_run:
        console.print("Dry run complete. No client process launched.")
        raise typer.Exit(code=0)

    if ensure_daemon_running:
        started, message = start_daemon(settings)
        console.print(message)
        if not started and "ya operativo" not in message:
            raise typer.Exit(code=1)

    try:
        exit_code = run_wrapped_command(command, extra_env)
    except FileNotFoundError as exc:
        console.print(f"Comando no encontrado: {exc.filename}")
        raise typer.Exit(code=127) from exc

    raise typer.Exit(code=exit_code)


@profile_app.command("list")
def list_profiles() -> None:
    settings = ensure_settings(default_settings_path())
    for name in settings.profiles:
        default_marker = " (default)" if name == settings.default_profile else ""
        console.print(f"- {name}{default_marker}")


@profile_app.command("show")
def show_profile(name: str | None = None) -> None:
    settings = ensure_settings(default_settings_path())
    profile_name = name or settings.default_profile
    if profile_name not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {profile_name}")
    console.print(build_profile_table(settings, profile_name))


@profile_app.command("create")
def create_profile(
    name: str,
    client: str = typer.Option("codex-cli"),
    mcp: list[str] = typer.Option(None, "--mcp"),
) -> None:
    path = default_settings_path()
    settings = ensure_settings(path)
    if name in settings.profiles:
        raise typer.BadParameter(f"Perfil ya existe: {name}")
    enabled_mcps = _validate_mcps(mcp)
    settings.profiles[name] = ProfileConfig(client=client, enabled_mcps=enabled_mcps)
    save_settings(path, settings)
    console.print(f"Perfil creado: {name}")


@profile_app.command("delete")
def delete_profile(name: str) -> None:
    path = default_settings_path()
    settings = ensure_settings(path)
    if name not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {name}")
    if name == settings.default_profile:
        console.print("No puedes eliminar el perfil por defecto en uso")
        raise typer.Exit(code=1)
    del settings.profiles[name]
    save_settings(path, settings)
    console.print(f"Perfil eliminado: {name}")


@profile_app.command("clone")
def clone_profile(source: str, target: str) -> None:
    path = default_settings_path()
    settings = ensure_settings(path)
    if source not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {source}")
    if target in settings.profiles:
        raise typer.BadParameter(f"Perfil ya existe: {target}")
    settings.profiles[target] = settings.profiles[source].model_copy(deep=True)
    save_settings(path, settings)
    console.print(f"Perfil clonado: {source} -> {target}")


@profile_app.command("set-mcps")
def set_profile_mcps(profile_name: str, mcps: list[str] = typer.Argument(...)) -> None:
    path = default_settings_path()
    settings, profile = _settings_and_profile(path, profile_name)
    profile.enabled_mcps = _validate_mcps(list(mcps))
    save_settings(path, settings)
    console.print(f"MCP actualizados para perfil {profile_name}")


@profile_app.command("set-client")
def set_profile_client(profile_name: str, client: str) -> None:
    path = default_settings_path()
    settings, profile = _settings_and_profile(path, profile_name)
    profile.client = client
    save_settings(path, settings)
    console.print(f"Cliente actualizado para perfil {profile_name}: {client}")


@profile_app.command("set-workspace-policy")
def set_profile_workspace_policy(
    profile_name: str,
    mode: str,
    path_value: Path | None = typer.Option(None, "--path"),
) -> None:
    path = default_settings_path()
    settings, profile = _settings_and_profile(path, profile_name)
    normalized_mode = mode.strip().lower()

    if normalized_mode == "explicit":
        if path_value is not None:
            raise typer.BadParameter("No puedes usar --path con workspace_policy=explicit")
        profile.workspace_policy = WorkspacePolicy(mode="explicit")
    elif normalized_mode == "fixed":
        if path_value is None:
            raise typer.BadParameter("Debes indicar --path cuando workspace_policy=fixed")
        resolved_path = path_value.expanduser().resolve()
        profile.workspace_policy = WorkspacePolicy(mode="fixed", path=str(resolved_path))
    else:
        raise typer.BadParameter("Workspace policy desconocida. Usa: explicit o fixed")

    save_settings(path, settings)
    console.print(f"Workspace policy actualizada para perfil {profile_name}: {normalized_mode}")


@service_app.command("show")
def show_profile_services(name: str | None = None) -> None:
    settings = ensure_settings(default_settings_path())
    profile_name = name or settings.default_profile
    if profile_name not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {profile_name}")
    console.print(build_profile_services_table(settings, profile_name))


@service_app.command("set")
def set_profile_service(
    profile_name: str,
    service_name: str,
    host: str | None = typer.Option(None),
    port: int | None = typer.Option(None),
    database: str | None = typer.Option(None),
    user: str | None = typer.Option(None),
    secret_ref: str | None = typer.Option(None),
) -> None:
    path = default_settings_path()
    settings = ensure_settings(path)
    if profile_name not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {profile_name}")

    profile = settings.profiles[profile_name]
    current = profile.services.get(service_name, ServiceConfig())
    updated = current.model_copy(
        update={
            key: value
            for key, value in {
                "host": host,
                "port": port,
                "database": database,
                "user": user,
                "secret_ref": secret_ref,
            }.items()
            if value is not None
        }
    )
    profile.services[service_name] = updated
    save_settings(path, settings)
    console.print(f"Servicio actualizado: {service_name} en perfil {profile_name}")


@service_app.command("remove")
def remove_profile_service(profile_name: str, service_name: str) -> None:
    path = default_settings_path()
    settings = ensure_settings(path)
    if profile_name not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {profile_name}")
    removed = settings.profiles[profile_name].services.pop(service_name, None)
    if removed is None:
        console.print(f"Servicio no encontrado: {service_name}")
        raise typer.Exit(code=1)
    save_settings(path, settings)
    console.print(f"Servicio eliminado: {service_name} del perfil {profile_name}")


@profile_app.command("use")
def use_profile(name: str) -> None:
    path = default_settings_path()
    settings = ensure_settings(path)
    if name not in settings.profiles:
        raise typer.BadParameter(f"Perfil desconocido: {name}")
    settings.default_profile = name
    save_settings(path, settings)
    console.print(f"Perfil por defecto actualizado: {name}")


@app.command()
def onboarding(force: bool = typer.Option(False, help="Overwrite existing settings")) -> None:
    path = default_settings_path()
    intro_settings, created = bootstrap_settings(path, force=force)
    profile = intro_settings.profiles[intro_settings.default_profile]
    console.print(f"Initial configuration created at {path}" if created else f"Existing configuration reused from {path}")
    console.print(
        build_onboarding_intro(
            workspace=str(Path.cwd()),
            settings_path=str(path),
            default_profile=intro_settings.default_profile,
            client_target=profile.client,
        )
    )
    console.print(build_preflight_table(build_preflight_checks(intro_settings, root=path.parent)))
    settings, _ = run_guided_onboarding(path, force=force)
    console.print(onboarding_summary(settings, path))
    console.print(
        build_onboarding_summary_panel(
            profile_name=settings.default_profile,
            enabled_mcps=settings.profiles[settings.default_profile].enabled_mcps,
            configured_services=configured_service_names(settings),
            secret_refs=registered_secret_refs(root=path.parent),
            secret_backend=secret_backend_name(),
            pending_items=build_pending_items(settings, root=path.parent),
        )
    )


if __name__ == "__main__":
    app()
