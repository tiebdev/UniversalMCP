"""Settings loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from universal_mcp.config.profiles import ProfileConfig


class RuntimeConfig(BaseModel):
    port: int = 8765


class Settings(BaseModel):
    default_profile: str = "work"
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    profiles: dict[str, ProfileConfig] = Field(
        default_factory=lambda: {
            "work": ProfileConfig(
                enabled_mcps=["filesystem", "git", "github", "postgres", "ast-grep"]
            )
        }
    )


def default_settings_path() -> Path:
    return Path.cwd() / ".universal_mcp.json"


def load_settings(path: Path) -> Settings:
    if not path.exists():
        return Settings()
    return Settings.model_validate_json(path.read_text(encoding="utf-8"))


def save_settings(path: Path, settings: Settings) -> None:
    path.write_text(json.dumps(settings.model_dump(mode="json"), indent=2), encoding="utf-8")


def ensure_settings(path: Path) -> Settings:
    settings = load_settings(path)
    if not path.exists():
        save_settings(path, settings)
    return settings
