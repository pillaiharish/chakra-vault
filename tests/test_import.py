from __future__ import annotations


def test_package_imports() -> None:
    import chakra_vault

    assert chakra_vault.__name__ == "chakra_vault"
