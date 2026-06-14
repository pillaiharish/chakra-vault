from __future__ import annotations


def test_package_imports() -> None:
    import chakra_vault

    assert chakra_vault.__name__ == "chakra_vault"


def test_download_modules_import() -> None:
    import chakra_vault.downloads.service
    import chakra_vault.downloads.throttle

    assert chakra_vault.downloads.service.__name__ == "chakra_vault.downloads.service"
    assert chakra_vault.downloads.throttle.__name__ == "chakra_vault.downloads.throttle"


def test_verify_modules_import() -> None:
    import chakra_vault.verify.hasher
    import chakra_vault.verify.types
    import chakra_vault.verify.verifier

    assert chakra_vault.verify.hasher.__name__ == "chakra_vault.verify.hasher"
    assert chakra_vault.verify.types.__name__ == "chakra_vault.verify.types"
    assert chakra_vault.verify.verifier.__name__ == "chakra_vault.verify.verifier"
