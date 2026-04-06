from universal_mcp.config.catalog import CatalogEntry, RiskLevel, SharingMode
from universal_mcp.config.profiles import ProfileConfig, ServiceConfig
from universal_mcp.daemon.server import (
    _build_external_preflight,
    _external_error_detail,
    _preflight_errors_by_name,
    _service_env,
)
from universal_mcp.daemon.state import ManagedProcessStatus, ProcessState


class _RouterStub:
    def __init__(self, states: dict[str, ProcessState]) -> None:
        self._states = states

    def managed_names(self) -> list[str]:
        return list(self._states.keys())

    def get_status(self, name: str) -> ManagedProcessStatus:
        return ManagedProcessStatus(name=name, state=self._states[name])


def test_service_env_maps_github_secret_name(monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_MCP_SECRET_GITHUB_TOKEN", "token-123")
    env = _service_env("github", ServiceConfig(secret_ref="github_token"))
    assert env["GITHUB_PERSONAL_ACCESS_TOKEN"] == "token-123"


def test_github_preflight_reports_missing_secret() -> None:
    profile = ProfileConfig(enabled_mcps=["github"], services={"github": ServiceConfig()})
    catalog = [
        CatalogEntry(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            required_secrets=["github_token"],
            risk=RiskLevel.HIGH,
            sharing_mode=SharingMode.PROFILE,
        )
    ]
    errors = _preflight_errors_by_name(profile, catalog)
    assert errors["github"] == ["Missing required secret: github_token"]


def test_postgres_preflight_reports_missing_secret() -> None:
    profile = ProfileConfig(enabled_mcps=["postgres"], services={"postgres": ServiceConfig()})
    catalog = [
        CatalogEntry(
            name="postgres",
            command="npx",
            args=["-y", "mcp-postgres-server"],
            required_secrets=["postgres_password"],
            risk=RiskLevel.HIGH,
            sharing_mode=SharingMode.PROFILE,
        )
    ]
    errors = _preflight_errors_by_name(profile, catalog)
    assert errors["postgres"] == [
        "Missing required secret: postgres_password",
        "Missing required setting: postgres.host",
        "Missing required setting: postgres.port",
        "Missing required setting: postgres.user",
        "Missing required setting: postgres.database",
    ]


def test_build_external_preflight_uses_catalog_and_router_state() -> None:
    preflight = _build_external_preflight(
        name="postgres",
        enabled_names=["postgres"],
        external_catalog_by_name={
            "postgres": CatalogEntry(
                name="postgres",
                command="npx",
                args=["-y", "mcp-postgres-server"],
                required_secrets=["postgres_password"],
                risk=RiskLevel.HIGH,
                sharing_mode=SharingMode.PROFILE,
            )
        },
        env_by_name={"postgres": {"PG_HOST": "localhost", "PG_PASSWORD": "pw"}},
        preflight_errors_by_name={"postgres": []},
        router=_RouterStub({"postgres": ProcessState.HEALTHY}),
    )
    assert preflight.name == "postgres"
    assert preflight.enabled is True
    assert preflight.required_env_present is True
    assert preflight.process_state == ProcessState.HEALTHY
    assert preflight.env_keys == ["PG_HOST", "PG_PASSWORD"]


def test_external_error_detail_contains_context() -> None:
    detail = _external_error_detail(
        "postgres",
        "tools/call:connect_db",
        "req-123",
        RuntimeError("connect ECONNREFUSED 127.0.0.1:5432"),
    )
    assert detail["request_id"] == "req-123"
    assert detail["mcp_name"] == "postgres"
    assert detail["action"] == "tools/call:connect_db"
    assert "ECONNREFUSED" in detail["error"]


def test_ast_grep_preflight_reports_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr("universal_mcp.daemon.server.shutil.which", lambda name: None)
    profile = ProfileConfig(enabled_mcps=["ast-grep"])
    catalog = [
        CatalogEntry(
            name="ast-grep",
            command="uvx",
            args=["--from", "git+https://github.com/ast-grep/ast-grep-mcp", "ast-grep-server"],
            risk=RiskLevel.LOW,
            sharing_mode=SharingMode.WORKSPACE,
        )
    ]
    errors = _preflight_errors_by_name(profile, catalog)
    assert errors["ast-grep"] == ["Missing required command: ast-grep"]
