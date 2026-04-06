from universal_mcp.config.catalog import catalog_names, load_default_catalog


def test_catalog_has_expected_entries() -> None:
    names = catalog_names()
    assert names == [
        "filesystem",
        "git",
        "github",
        "postgres",
        "ast-grep",
        "sequential-thinking",
    ]
    assert len(load_default_catalog()) == 6

