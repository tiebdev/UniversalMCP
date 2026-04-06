import json
import os
import sys
from pathlib import Path

from typer.testing import CliRunner

from universal_mcp.cli.main import app
from universal_mcp.cli.wrapper import build_wrapper_env
from universal_mcp.config.settings import Settings


runner = CliRunner()


def _default_onboarding_input() -> str:
    return "\n".join(
        [
            "y",  # filesystem
            "y",  # git
            "n",  # github
            "n",  # postgres
            "y",  # ast-grep
            "n",  # sequential-thinking
        ]
    ) + "\n"


def test_build_wrapper_env_contains_runtime_values(tmp_path: Path) -> None:
    settings = Settings()
    env = build_wrapper_env(settings=settings, profile_name="work", workspace=tmp_path)
    assert env["UNIVERSAL_MCP_DAEMON_URL"] == "http://127.0.0.1:8765"
    assert env["UNIVERSAL_MCP_PROFILE"] == "work"
    assert env["UNIVERSAL_MCP_WORKSPACE"] == str(tmp_path)


def test_onboarding_creates_settings_file() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["onboarding"], input=_default_onboarding_input())
        assert result.exit_code == 0
        assert Path(".universal_mcp.json").exists()
        assert "System: Universal Model Context Protocol (MCP) [1.0.0]" in result.stdout
        assert "Initial configuration created" in result.stdout
        assert "Settings Path:" in result.stdout
        assert "Enabled MCPs" in result.stdout
        assert "Enable sequential-thinking? [Y/n]" in result.stdout


def test_profile_use_persists_default_profile() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["onboarding"], input=_default_onboarding_input())
        settings_path = Path(".universal_mcp.json")
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        payload["profiles"]["personal"] = payload["profiles"]["work"]
        settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        result = runner.invoke(app, ["profile", "use", "personal"])
        assert result.exit_code == 0
        updated = json.loads(settings_path.read_text(encoding="utf-8"))
        assert updated["default_profile"] == "personal"


def test_profile_create_clone_set_mcps_and_delete() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["onboarding"], input=_default_onboarding_input())
        settings_path = Path(".universal_mcp.json")

        create_result = runner.invoke(
            app,
            [
                "profile",
                "create",
                "lab",
                "--mcp",
                "filesystem",
                "--mcp",
                "git",
            ],
        )
        clone_result = runner.invoke(app, ["profile", "clone", "lab", "lab-copy"])
        set_mcps_result = runner.invoke(
            app,
            ["profile", "set-mcps", "lab-copy", "filesystem", "sequential-thinking"],
        )
        delete_result = runner.invoke(app, ["profile", "delete", "lab"])

        assert create_result.exit_code == 0
        assert "Perfil creado: lab" in create_result.stdout
        assert clone_result.exit_code == 0
        assert "Perfil clonado: lab -> lab-copy" in clone_result.stdout
        assert set_mcps_result.exit_code == 0
        assert "MCP actualizados para perfil lab-copy" in set_mcps_result.stdout
        assert delete_result.exit_code == 0
        assert "Perfil eliminado: lab" in delete_result.stdout

        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "lab" not in payload["profiles"]
        assert payload["profiles"]["lab-copy"]["enabled_mcps"] == ["filesystem", "sequential-thinking"]


def test_profile_delete_rejects_default_profile() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["onboarding"], input=_default_onboarding_input())
        result = runner.invoke(app, ["profile", "delete", "work"])
        assert result.exit_code != 0
        assert "No puedes eliminar el perfil por defecto en uso" in result.stdout


def test_run_injects_environment_without_starting_daemon() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["onboarding"], input=_default_onboarding_input())
        output_path = Path("env.json").resolve()
        command = [
            "run",
            "--no-ensure-daemon",
            sys.executable,
            "-c",
            (
                "import json,os,pathlib;"
                f"path=pathlib.Path(r'{output_path}');"
                "path.write_text(json.dumps({k:os.environ[k] for k in "
                "['UNIVERSAL_MCP_DAEMON_URL','UNIVERSAL_MCP_PROFILE','UNIVERSAL_MCP_WORKSPACE']}),"
                "encoding='utf-8')"
            ),
        ]
        result = runner.invoke(app, command)
        assert result.exit_code == 0
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["UNIVERSAL_MCP_DAEMON_URL"] == "http://127.0.0.1:8765"
        assert payload["UNIVERSAL_MCP_PROFILE"] == "work"
        assert payload["UNIVERSAL_MCP_WORKSPACE"] == os.getcwd()


def test_catalog_and_doctor_render() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["onboarding"], input=_default_onboarding_input())
        catalog_result = runner.invoke(app, ["catalog"])
        doctor_result = runner.invoke(app, ["doctor"])
        assert catalog_result.exit_code == 0
        assert "Catalogo MCP" in catalog_result.stdout
        assert "filesystem" in catalog_result.stdout
        assert doctor_result.exit_code == 0
        assert "Doctor (work)" in doctor_result.stdout


def test_profile_show_renders_default_profile() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["onboarding"], input=_default_onboarding_input())
        result = runner.invoke(app, ["profile", "show"])
        assert result.exit_code == 0
        assert "Perfil: work" in result.stdout
        assert "filesystem" in result.stdout


def test_secret_set_and_list_commands() -> None:
    with runner.isolated_filesystem():
        set_result = runner.invoke(app, ["secret", "set", "github_token", "secret-123"])
        list_result = runner.invoke(app, ["secret", "list"])
        assert set_result.exit_code == 0
        assert "Secreto actualizado" in set_result.stdout
        assert list_result.exit_code == 0
        assert "github_token" in list_result.stdout


def test_profile_service_set_and_show_commands() -> None:
    with runner.isolated_filesystem():
        runner.invoke(app, ["onboarding"], input=_default_onboarding_input())
        set_result = runner.invoke(
            app,
            [
                "profile",
                "service",
                "set",
                "work",
                "postgres",
                "--host",
                "127.0.0.1",
                "--port",
                "5432",
                "--database",
                "app",
                "--user",
                "postgres",
                "--secret-ref",
                "postgres_password",
            ],
        )
        show_result = runner.invoke(app, ["profile", "service", "show"])
        assert set_result.exit_code == 0
        assert "Servicio actualizado" in set_result.stdout
        assert show_result.exit_code == 0
        assert "postgres" in show_result.stdout
        assert "postgres_password" in show_result.stdout


def test_onboarding_guides_github_and_postgres_setup() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["onboarding", "--force"],
            input="\n".join(
                [
                    "y",  # filesystem
                    "y",  # git
                    "y",  # github
                    "y",  # postgres
                    "n",  # ast-grep
                    "n",  # sequential-thinking
                    "",  # github host default
                    "ghp-demo-token",
                    "ghp-demo-token",
                    "db.local",
                    "55432",
                    "umcp_test",
                    "postgres",
                    "pw-demo",
                    "pw-demo",
                ]
            )
            + "\n",
        )
        assert result.exit_code == 0

        settings_path = Path(".universal_mcp.json")
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        profile = payload["profiles"]["work"]
        assert "github" in profile["enabled_mcps"]
        assert "postgres" in profile["enabled_mcps"]
        assert profile["services"]["github"]["secret_ref"] == "github_token"
        assert profile["services"]["postgres"]["host"] == "db.local"
        assert profile["services"]["postgres"]["port"] == 55432
        assert profile["services"]["postgres"]["database"] == "umcp_test"
        assert profile["services"]["postgres"]["user"] == "postgres"
        assert profile["services"]["postgres"]["secret_ref"] == "postgres_password"

        secrets_payload = json.loads(Path(".universal_mcp.secrets.json").read_text(encoding="utf-8"))
        assert secrets_payload["refs"]["github_token"]["value"] == "ghp-demo-token"
        assert secrets_payload["refs"]["postgres_password"]["value"] == "pw-demo"
