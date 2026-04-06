"""V1 MCP catalog definitions."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SharingMode(str, Enum):
    GLOBAL = "global"
    WORKSPACE = "workspace"
    PROFILE = "profile"


class IntegrationKind(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class CatalogEntry(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    required_secrets: list[str] = Field(default_factory=list)
    risk: RiskLevel
    sharing_mode: SharingMode
    integration_kind: IntegrationKind = IntegrationKind.EXTERNAL
    enabled_by_default: bool = True


def load_default_catalog() -> list[CatalogEntry]:
    return [
        CatalogEntry(
            name="filesystem",
            command="npx",
            risk=RiskLevel.MEDIUM,
            sharing_mode=SharingMode.WORKSPACE,
            integration_kind=IntegrationKind.INTERNAL,
        ),
        CatalogEntry(
            name="git",
            command="uvx",
            args=["mcp-server-git"],
            risk=RiskLevel.MEDIUM,
            sharing_mode=SharingMode.WORKSPACE,
            integration_kind=IntegrationKind.INTERNAL,
        ),
        CatalogEntry(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            required_secrets=["github_token"],
            risk=RiskLevel.HIGH,
            sharing_mode=SharingMode.PROFILE,
        ),
        CatalogEntry(
            name="postgres",
            command="npx",
            args=["-y", "mcp-postgres-server"],
            required_secrets=["postgres_password"],
            risk=RiskLevel.HIGH,
            sharing_mode=SharingMode.PROFILE,
        ),
        CatalogEntry(
            name="ast-grep",
            command="uvx",
            args=["--from", "git+https://github.com/ast-grep/ast-grep-mcp", "ast-grep-server"],
            risk=RiskLevel.LOW,
            sharing_mode=SharingMode.WORKSPACE,
        ),
        CatalogEntry(
            name="sequential-thinking",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
            risk=RiskLevel.LOW,
            sharing_mode=SharingMode.GLOBAL,
        ),
    ]


def catalog_names() -> list[str]:
    return [entry.name for entry in load_default_catalog()]


def filter_catalog(entries: list[CatalogEntry], enabled_names: list[str]) -> list[CatalogEntry]:
    enabled = set(enabled_names)
    return [entry for entry in entries if entry.name in enabled]


def split_catalog(entries: list[CatalogEntry]) -> tuple[list[CatalogEntry], list[CatalogEntry]]:
    internal = [entry for entry in entries if entry.integration_kind == IntegrationKind.INTERNAL]
    external = [entry for entry in entries if entry.integration_kind == IntegrationKind.EXTERNAL]
    return internal, external
