"""Secret storage with optional keyring backend and local fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

SERVICE_NAME = "universal-mcp"


class SecretRecord(BaseModel):
    ref: str
    backend: str
    has_value: bool = False


class SecretIndexEntry(BaseModel):
    backend: str
    value: str | None = None


class SecretIndex(BaseModel):
    refs: dict[str, SecretIndexEntry] = Field(default_factory=dict)


class SecretBackendStatus(BaseModel):
    name: str
    available: bool
    detail: str


def secret_backend_name() -> str:
    return secret_backend_status().name


def secret_backend_status() -> SecretBackendStatus:
    keyring = _keyring_module()
    if keyring is None:
        return SecretBackendStatus(
            name="fallback",
            available=False,
            detail="keyring module unavailable, using local fallback",
        )

    try:
        backend = keyring.get_keyring()
    except Exception as exc:
        return SecretBackendStatus(
            name="fallback",
            available=False,
            detail=f"keyring backend unavailable ({exc.__class__.__name__}), using local fallback",
        )

    if not _is_usable_keyring_backend(backend):
        backend_name = type(backend).__name__
        return SecretBackendStatus(
            name="fallback",
            available=False,
            detail=f"keyring backend not usable ({backend_name}), using local fallback",
        )

    backend_name = type(backend).__name__
    return SecretBackendStatus(
        name="keyring",
        available=True,
        detail=f"keyring available ({backend_name})",
    )


def default_secret_store_path(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / ".universal_mcp.secrets.json"


def list_secret_records(root: Path | None = None) -> list[SecretRecord]:
    index = _load_index(default_secret_store_path(root))
    return [
        SecretRecord(ref=ref, backend=entry.backend, has_value=entry.value is not None)
        for ref, entry in sorted(index.refs.items())
    ]


def set_secret(ref: str, value: str, root: Path | None = None) -> SecretRecord:
    index_path = default_secret_store_path(root)
    index = _load_index(index_path)
    backend_status = secret_backend_status()

    if backend_status.name == "keyring":
        keyring = _keyring_module()
        try:
            assert keyring is not None
            keyring.set_password(SERVICE_NAME, ref, value)
        except Exception:
            entry = SecretIndexEntry(backend="fallback", value=value)
        else:
            entry = SecretIndexEntry(backend="keyring", value=None)
    else:
        entry = SecretIndexEntry(backend="fallback", value=value)

    index.refs[ref] = entry
    _save_index(index_path, index)
    return SecretRecord(ref=ref, backend=entry.backend, has_value=entry.value is not None)


def get_secret(ref: str, root: Path | None = None) -> str | None:
    index = _load_index(default_secret_store_path(root))
    entry = index.refs.get(ref)
    if entry is None:
        return None

    if entry.backend == "keyring" and secret_backend_status().name == "keyring":
        keyring = _keyring_module()
        try:
            assert keyring is not None
            value = keyring.get_password(SERVICE_NAME, ref)
        except Exception:
            return None
        return value or None

    return entry.value


def delete_secret(ref: str, root: Path | None = None) -> bool:
    index_path = default_secret_store_path(root)
    index = _load_index(index_path)
    entry = index.refs.pop(ref, None)
    if entry is None:
        return False

    if entry.backend == "keyring" and secret_backend_status().name == "keyring":
        keyring = _keyring_module()
        try:
            assert keyring is not None
            keyring.delete_password(SERVICE_NAME, ref)
        except Exception:
            pass

    _save_index(index_path, index)
    return True


def _is_usable_keyring_backend(backend: Any) -> bool:
    backend_module = type(backend).__module__
    if backend_module.startswith("keyring.backends.fail"):
        return False

    priority = getattr(backend, "priority", None)
    if isinstance(priority, (int, float)) and priority <= 0:
        return False

    required_methods = ("get_password", "set_password", "delete_password")
    return all(callable(getattr(backend, method, None)) for method in required_methods)


def _load_index(path: Path) -> SecretIndex:
    if not path.exists():
        return SecretIndex()
    return SecretIndex.model_validate_json(path.read_text(encoding="utf-8"))


def _save_index(path: Path, index: SecretIndex) -> None:
    path.write_text(index.model_dump_json(indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _keyring_module():
    try:
        import keyring  # type: ignore
    except Exception:
        return None
    return keyring
