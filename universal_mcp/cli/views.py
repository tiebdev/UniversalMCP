"""Rich rendering helpers for CLI output."""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from rich.console import Group
from rich.text import Text
from rich.table import Table

from universal_mcp.config.catalog import CatalogEntry
from universal_mcp.config.secrets import SecretRecord
from universal_mcp.config.settings import Settings
from universal_mcp.daemon.state import DaemonStatus
from universal_mcp.daemon.server import _env_by_name, _preflight_errors_by_name


@dataclass(slots=True)
class PreflightCheck:
    status: str
    label: str
    detail: str


ASCII_BANNER = r"""
  ╔══════════════════════════════════════════════════════════════════════════╗
                                                                                                 
    ██╗   ██╗███╗   ██╗██╗██╗   ██╗███████╗██████╗ ███████╗  █████  ╔██╗    
    ██║   ██║████╗  ██║██║██║   ██║██╔════╝██╔══██╗██╔════╝ ██╔══██╗║██║     
    ██║   ██║██╔██╗ ██║██║██║   ██║█████╗  ██████╔╝███████╗ ███████║║██║     
    ██║   ██║██║╚██╗██║██║╚██╗ ██╔╝██╔══╝  ██╔══██╗╚════██║ ██╔══██║║██║     
     ██████  ██║ ╚████║██║ ╚████╔╝ ███████╗██║  ██║███████║ ██║  ██║║███████
     ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═╝  ╚═╝╚══════╝
                                                                        
                           ███╗   ███╗ ██████╗  ██████╗                          
                           ████╗ ████║██╔════╝  ██╔══██╗                         
                           ██╔████╔██║██║       ██████╔╝                         
                           ██║╚██╔╝██║██║       ██╔═══╝                          
                           ██║ ╚═╝ ██║ ██████╗  ██║                              
                           ╚═╝     ╚═╝ ╚═════╝  ╚═╝                        
                                                                        
  ╚══════════════════════════════════════════════════════════════════════════╝
""".strip("\n")


def build_onboarding_intro(
    *,
    workspace: str,
    settings_path: str,
    default_profile: str,
    client_target: str,
) -> Group:
    details = Text(
        "\n".join(
            [
                "System: Universal Model Context Protocol (MCP) [0.1.0]",
                "Mode: First-Run Onboarding",
                f"Workspace: {workspace}",
                f"Settings Path: {settings_path}",
                f"Default Profile: {default_profile}",
                f"Client Target: {client_target}",
            ]
        ),
        style="bold",
    )
    return Group(
        Text(ASCII_BANNER, style="bold"),
        Text(""),
        details,
    )


def build_preflight_table(checks: list[PreflightCheck]) -> Table:
    table = Table()
    table.add_column("State")
    table.add_column("Check")
    table.add_column("Detail")
    for check in checks:
        state_text = {
            "OK": "[green]OK[/green]",
            "WARN": "[yellow]WARN[/yellow]",
            "INFO": "[cyan]INFO[/cyan]",
            "FAIL": "[red]FAIL[/red]",
        }.get(check.status, check.status)
        table.add_row(state_text, check.label, check.detail)
    return table


def build_onboarding_summary_panel(
    *,
    profile_name: str,
    enabled_mcps: list[str],
    configured_services: list[str],
    secret_refs: list[str],
    secret_backend: str,
    pending_items: list[str],
) -> Table:
    table = Table()
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Active Profile", profile_name)
    table.add_row("Enabled MCPs", ", ".join(enabled_mcps) or "-")
    table.add_row("Configured Services", ", ".join(configured_services) or "-")
    table.add_row("Registered Secrets", ", ".join(secret_refs) or "-")
    table.add_row("Secret Backend", secret_backend)
    table.add_row("Pending Items", ", ".join(pending_items) or "none")
    table.add_row("Next Commands", "mcp-cli doctor | mcp-cli start | mcp-cli run codex")
    return table


def build_status_table(status: DaemonStatus) -> Table:
    table = Table(title="Universal MCP Status")
    table.add_column("MCP")
    table.add_column("State")
    table.add_column("Restarts")
    table.add_column("Last Error")

    for process in status.processes:
        table.add_row(
            process.name,
            process.state.value,
            str(process.restart_count),
            process.last_error or "-",
        )

    return table


def build_run_context_table(
    *,
    profile_name: str,
    target_client: str,
    executable: str,
    workspace: str,
    daemon_url: str,
    ensure_daemon_running: bool,
    dry_run: bool,
) -> Table:
    table = Table(title="Run Context")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Profile", profile_name)
    table.add_row("Target Client", target_client)
    table.add_row("Executable", executable)
    table.add_row("Workspace", workspace)
    table.add_row("Daemon URL", daemon_url)
    table.add_row("Ensure Daemon", "yes" if ensure_daemon_running else "no")
    table.add_row("Dry Run", "yes" if dry_run else "no")
    return table


def build_catalog_table(entries: list[CatalogEntry]) -> Table:
    table = Table(title="Catalogo MCP")
    table.add_column("MCP")
    table.add_column("Kind")
    table.add_column("Risk")
    table.add_column("Sharing")
    table.add_column("Secrets")

    for entry in entries:
        table.add_row(
            entry.name,
            entry.integration_kind.value,
            entry.risk.value,
            entry.sharing_mode.value,
            ", ".join(entry.required_secrets) or "-",
        )

    return table


def build_profile_table(settings: Settings, profile_name: str) -> Table:
    profile = settings.profiles[profile_name]
    table = Table(title=f"Perfil: {profile_name}")
    table.add_column("Campo")
    table.add_column("Valor")
    table.add_row("Cliente", profile.client)
    table.add_row("MCP habilitados", ", ".join(profile.enabled_mcps) or "-")
    table.add_row("Workspace policy", profile.workspace_policy.mode)
    table.add_row("Workspace path", profile.workspace_policy.path or "-")
    services = ", ".join(sorted(profile.services.keys())) or "-"
    table.add_row("Servicios", services)
    return table


def build_doctor_table(settings: Settings, entries: list[CatalogEntry]) -> Table:
    profile_name = settings.default_profile
    profile = settings.profiles.get(profile_name)
    enabled_entries = [entry for entry in entries if profile and entry.name in profile.enabled_mcps]
    env_by_name = _env_by_name(profile, [entry.name for entry in enabled_entries])
    errors_by_name = _preflight_errors_by_name(profile, enabled_entries)

    table = Table(title=f"Doctor ({profile_name})")
    table.add_column("MCP")
    table.add_column("Command")
    table.add_column("Env")
    table.add_column("Checks")

    for entry in enabled_entries:
        command_ok = shutil.which(entry.command) is not None
        env_keys = sorted(env_by_name.get(entry.name, {}).keys())
        errors = errors_by_name.get(entry.name, [])
        checks = "ok" if command_ok and not errors else "; ".join(
            ([f"missing command: {entry.command}"] if not command_ok else []) + errors
        )
        table.add_row(
            entry.name,
            "ok" if command_ok else "missing",
            ", ".join(env_keys) or "-",
            checks,
        )

    return table


def build_secrets_table(records: list[SecretRecord], usage_by_ref: dict[str, list[str]] | None = None) -> Table:
    table = Table(title="Secretos")
    table.add_column("Ref")
    table.add_column("Backend")
    table.add_column("Persistido")
    table.add_column("Usado por")

    for record in records:
        usage = usage_by_ref.get(record.ref, []) if usage_by_ref else []
        table.add_row(
            record.ref,
            record.backend,
            "si" if record.has_value or record.backend == "keyring" else "no",
            ", ".join(usage) or "-",
        )

    return table


def build_profile_services_table(settings: Settings, profile_name: str) -> Table:
    profile = settings.profiles[profile_name]
    table = Table(title=f"Servicios del perfil: {profile_name}")
    table.add_column("Servicio")
    table.add_column("Host")
    table.add_column("Port")
    table.add_column("Database")
    table.add_column("User")
    table.add_column("Secret Ref")

    for name, service in sorted(profile.services.items()):
        table.add_row(
            name,
            service.host or "-",
            str(service.port) if service.port is not None else "-",
            service.database or "-",
            service.user or "-",
            service.secret_ref or "-",
        )

    return table
