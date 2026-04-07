"""First-run onboarding helpers."""

from __future__ import annotations

import shutil
from pathlib import Path
import typer

from universal_mcp.cli.views import PreflightCheck
from universal_mcp.config.catalog import CatalogEntry, filter_catalog, load_default_catalog
from universal_mcp.config.profiles import ProfileConfig, ServiceConfig
from universal_mcp.config.secrets import (
    get_secret,
    list_secret_records,
    secret_backend_name,
    secret_backend_status,
    set_secret,
)
from universal_mcp.config.settings import Settings, save_settings
from universal_mcp.daemon.server import _preflight_errors_by_name


def onboarding_summary(settings: Settings, path: Path | None = None) -> str:
    return f"Settings Path: {path}" if path else "Settings Path: -"


def bootstrap_settings(path: Path, *, force: bool = False) -> tuple[Settings, bool]:
    if path.exists() and not force:
        return Settings.model_validate_json(path.read_text(encoding="utf-8")), False

    settings = Settings()
    save_settings(path, settings)
    return settings, True


def build_preflight_checks(settings: Settings, *, root: Path) -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    profile = settings.profiles[settings.default_profile]
    catalog = load_default_catalog()
    enabled_catalog = filter_catalog(catalog, profile.enabled_mcps)
    errors_by_name = _preflight_errors_by_name(profile, enabled_catalog, root=root)

    checks.append(
        PreflightCheck(
            status="OK",
            label="Settings schema validated",
            detail=f"default profile: {settings.default_profile}",
        )
    )
    checks.append(
        PreflightCheck(
            status="OK",
            label="Workspace resolved",
            detail=str(root),
        )
    )
    checks.append(
        PreflightCheck(
            status="OK",
            label="MCP catalog loaded",
            detail=f"{len(catalog)} entries available",
        )
    )

    backend = secret_backend_status()
    checks.append(
        PreflightCheck(
            status="OK" if backend.available else "INFO",
            label="Secret backend detected",
            detail=backend.detail,
        )
    )

    for entry in enabled_catalog:
        command_ok = shutil.which(entry.command) is not None
        checks.append(
            PreflightCheck(
                status="OK" if command_ok else "WARN",
                label=f"{entry.name} command",
                detail=entry.command if command_ok else f"missing command: {entry.command}",
            )
        )
        entry_errors = errors_by_name.get(entry.name, [])
        checks.append(
            PreflightCheck(
                status="OK" if not entry_errors else "WARN",
                label=f"{entry.name} requirements",
                detail="ready" if not entry_errors else "; ".join(entry_errors),
            )
        )

    return checks


def run_guided_onboarding(path: Path, *, force: bool = False) -> tuple[Settings, bool]:
    settings, created = bootstrap_settings(path, force=force)
    profile_name = settings.default_profile
    profile = settings.profiles.setdefault(profile_name, ProfileConfig())

    selected_mcps = _prompt_enabled_mcps(profile)
    profile.enabled_mcps = selected_mcps

    if "github" in selected_mcps:
        profile.services["github"] = _configure_github_service(
            profile.services.get("github"),
            root=path.parent,
        )
    else:
        profile.services.pop("github", None)

    if "postgres" in selected_mcps:
        profile.services["postgres"] = _configure_postgres_service(
            profile.services.get("postgres"),
            root=path.parent,
        )
    else:
        profile.services.pop("postgres", None)

    save_settings(path, settings)
    return settings, created


def _prompt_enabled_mcps(profile: ProfileConfig) -> list[str]:
    entries = load_default_catalog()
    enabled_now = set(profile.enabled_mcps)
    selected: list[str] = []
    typer.echo("")
    typer.echo("Guided setup: MCP selection")
    for entry in entries:
        default_enabled = (
            entry.name in enabled_now
            or (not enabled_now and entry.enabled_by_default)
            or (entry.name == "sequential-thinking" and entry.enabled_by_default)
        )
        if typer.confirm(f"Enable {entry.name}?", default=default_enabled):
            selected.append(entry.name)
    return selected


def _configure_github_service(current: ServiceConfig | None, *, root: Path) -> ServiceConfig:
    current = current or ServiceConfig(secret_ref="github_token")
    secret_ref = current.secret_ref or "github_token"

    typer.echo("")
    typer.echo("Guided setup: github")
    host_default = current.host or ""
    host_value = typer.prompt("GitHub API URL (press enter to keep default)", default=host_default, show_default=False)
    _handle_secret_prompt(
        secret_ref=secret_ref,
        root=root,
        prompt_label="GitHub personal access token",
    )

    return current.model_copy(
        update={
            "host": host_value or None,
            "secret_ref": secret_ref,
        }
    )


def _configure_postgres_service(current: ServiceConfig | None, *, root: Path) -> ServiceConfig:
    current = current or ServiceConfig(secret_ref="postgres_password")
    secret_ref = current.secret_ref or "postgres_password"

    typer.echo("")
    typer.echo("Guided setup: postgres")
    host = typer.prompt("Postgres host", default=current.host or "127.0.0.1")
    port = typer.prompt("Postgres port", default=str(current.port or 5432))
    database = typer.prompt("Postgres database", default=current.database or "app")
    user = typer.prompt("Postgres user", default=current.user or "postgres")

    _handle_secret_prompt(
        secret_ref=secret_ref,
        root=root,
        prompt_label="Postgres password",
    )

    return current.model_copy(
        update={
            "host": host,
            "port": int(port),
            "database": database,
            "user": user,
            "secret_ref": secret_ref,
        }
    )


def _handle_secret_prompt(*, secret_ref: str, root: Path, prompt_label: str) -> None:
    existing = get_secret(secret_ref, root=root)
    if existing:
        typer.echo(f"Existing secret detected for {secret_ref}.")
        action = _prompt_secret_action()
        if action == "reuse" or action == "":
            return
        if action == "skip":
            typer.echo(f"Configuration postponed for secret {secret_ref}.")
            return
    else:
        action = "replace"

    value = typer.prompt(prompt_label, hide_input=True, confirmation_prompt=True)
    set_secret(secret_ref, value, root=root)


def _prompt_secret_action() -> str:
    while True:
        action = typer.prompt(
            "Action [reuse/replace/skip]",
            default="reuse",
            show_default=True,
        ).strip().lower()
        if action in {"", "reuse", "replace", "skip"}:
            return action
        typer.echo("Invalid action. Use: reuse, replace, or skip.")


def build_pending_items(settings: Settings, *, root: Path) -> list[str]:
    profile = settings.profiles[settings.default_profile]
    enabled_catalog = filter_catalog(load_default_catalog(), profile.enabled_mcps)
    pending: list[str] = []
    for name, errors in _preflight_errors_by_name(profile, enabled_catalog, root=root).items():
        if errors:
            pending.append(f"{name}: {', '.join(errors)}")
    return pending


def configured_service_names(settings: Settings) -> list[str]:
    profile = settings.profiles[settings.default_profile]
    return sorted(profile.services.keys())


def registered_secret_refs(*, root: Path) -> list[str]:
    return [record.ref for record in list_secret_records(root=root)]
