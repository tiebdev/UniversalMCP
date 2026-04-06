import os
from pathlib import Path

from universal_mcp.config.profiles import ProfileConfig, ServiceConfig
from universal_mcp.config.secrets import set_secret
from universal_mcp.daemon.server import _env_by_name, _resolve_secret, _service_env


def test_resolve_secret_prefers_universal_prefix(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_MCP_SECRET_GITHUB_TOKEN", "secret-value")
    assert _resolve_secret("github_token") == "secret-value"


def test_service_env_maps_service_fields(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_MCP_SECRET_POSTGRES_PASSWORD", "pw")
    env = _service_env(
        "postgres",
        ServiceConfig(
            secret_ref="postgres_password",
            host="db.internal",
            port=5432,
            database="app",
            user="app_user",
        ),
    )
    assert env["PG_HOST"] == "db.internal"
    assert env["PG_PORT"] == "5432"
    assert env["PG_DATABASE"] == "app"
    assert env["PG_USER"] == "app_user"
    assert env["PG_PASSWORD"] == "pw"


def test_env_by_name_filters_to_enabled_services(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_MCP_SECRET_GITHUB_TOKEN", "gh")
    profile = ProfileConfig(
        enabled_mcps=["github"],
        services={
            "github": ServiceConfig(secret_ref="github_token"),
            "postgres": ServiceConfig(secret_ref="postgres_password"),
        },
    )
    env = _env_by_name(profile, ["github"])
    assert "github" in env
    assert "postgres" not in env
    assert env["github"]["GITHUB_PERSONAL_ACCESS_TOKEN"] == "gh"


def test_resolve_secret_uses_store_when_env_missing(tmp_path: Path) -> None:
    set_secret("github_token", "stored-secret", root=tmp_path)
    assert _resolve_secret("github_token", root=tmp_path) == "stored-secret"
