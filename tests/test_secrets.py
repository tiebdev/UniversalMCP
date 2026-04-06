from pathlib import Path

from universal_mcp.config.secrets import delete_secret, get_secret, list_secret_records, set_secret


def test_secret_store_fallback_roundtrip(tmp_path: Path) -> None:
    record = set_secret("github_token", "secret-123", root=tmp_path)
    assert record.ref == "github_token"
    assert get_secret("github_token", root=tmp_path) == "secret-123"
    records = list_secret_records(root=tmp_path)
    assert records[0].ref == "github_token"
    assert delete_secret("github_token", root=tmp_path) is True
    assert get_secret("github_token", root=tmp_path) is None
