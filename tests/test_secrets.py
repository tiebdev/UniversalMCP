from pathlib import Path

from universal_mcp.config import secrets
from universal_mcp.config.secrets import (
    delete_secret,
    get_secret,
    list_secret_records,
    secret_backend_name,
    secret_backend_status,
    set_secret,
)


class _MemoryBackend:
    priority = 1

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, ref: str) -> str | None:
        return self._store.get((service_name, ref))

    def set_password(self, service_name: str, ref: str, value: str) -> None:
        self._store[(service_name, ref)] = value

    def delete_password(self, service_name: str, ref: str) -> None:
        self._store.pop((service_name, ref), None)


class _FailBackend:
    __module__ = "keyring.backends.fail"
    priority = 0

    def get_password(self, service_name: str, ref: str) -> str | None:
        return None

    def set_password(self, service_name: str, ref: str, value: str) -> None:
        raise RuntimeError("backend disabled")

    def delete_password(self, service_name: str, ref: str) -> None:
        raise RuntimeError("backend disabled")


class _FakeKeyringModule:
    def __init__(self, backend: object) -> None:
        self._backend = backend

    def get_keyring(self) -> object:
        return self._backend

    def get_password(self, service_name: str, ref: str) -> str | None:
        return self._backend.get_password(service_name, ref)

    def set_password(self, service_name: str, ref: str, value: str) -> None:
        self._backend.set_password(service_name, ref, value)

    def delete_password(self, service_name: str, ref: str) -> None:
        self._backend.delete_password(service_name, ref)


class _ExplodingKeyringModule:
    def get_keyring(self) -> object:
        raise RuntimeError("no backend")


def test_secret_store_fallback_roundtrip(tmp_path: Path) -> None:
    record = set_secret("github_token", "secret-123", root=tmp_path)
    assert record.ref == "github_token"
    assert get_secret("github_token", root=tmp_path) == "secret-123"
    records = list_secret_records(root=tmp_path)
    assert records[0].ref == "github_token"
    assert delete_secret("github_token", root=tmp_path) is True
    assert get_secret("github_token", root=tmp_path) is None


def test_secret_backend_status_reports_fallback_when_module_missing(monkeypatch) -> None:
    monkeypatch.setattr(secrets, "_keyring_module", lambda: None)

    status = secret_backend_status()

    assert status.name == "fallback"
    assert status.available is False
    assert "module unavailable" in status.detail
    assert secret_backend_name() == "fallback"


def test_secret_backend_status_reports_keyring_when_backend_usable(monkeypatch) -> None:
    monkeypatch.setattr(secrets, "_keyring_module", lambda: _FakeKeyringModule(_MemoryBackend()))

    status = secret_backend_status()

    assert status.name == "keyring"
    assert status.available is True
    assert "keyring available" in status.detail
    assert secret_backend_name() == "keyring"


def test_secret_backend_status_reports_fallback_when_backend_is_unusable(monkeypatch) -> None:
    monkeypatch.setattr(secrets, "_keyring_module", lambda: _FakeKeyringModule(_FailBackend()))

    status = secret_backend_status()

    assert status.name == "fallback"
    assert status.available is False
    assert "not usable" in status.detail


def test_secret_backend_status_reports_fallback_when_keyring_backend_lookup_fails(monkeypatch) -> None:
    monkeypatch.setattr(secrets, "_keyring_module", lambda: _ExplodingKeyringModule())

    status = secret_backend_status()

    assert status.name == "fallback"
    assert status.available is False
    assert "backend unavailable" in status.detail


def test_secret_store_uses_keyring_when_backend_is_usable(monkeypatch, tmp_path: Path) -> None:
    backend = _MemoryBackend()
    monkeypatch.setattr(secrets, "_keyring_module", lambda: _FakeKeyringModule(backend))

    record = set_secret("github_token", "secret-123", root=tmp_path)

    assert record.backend == "keyring"
    assert record.has_value is False
    assert get_secret("github_token", root=tmp_path) == "secret-123"
    assert list_secret_records(root=tmp_path)[0].backend == "keyring"
    assert delete_secret("github_token", root=tmp_path) is True
    assert get_secret("github_token", root=tmp_path) is None


def test_secret_store_falls_back_when_keyring_backend_is_not_usable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets, "_keyring_module", lambda: _FakeKeyringModule(_FailBackend()))

    record = set_secret("github_token", "secret-123", root=tmp_path)

    assert record.backend == "fallback"
    assert record.has_value is True
    assert get_secret("github_token", root=tmp_path) == "secret-123"
