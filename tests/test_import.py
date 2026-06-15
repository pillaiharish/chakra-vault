from __future__ import annotations


def test_package_imports() -> None:
    import chakra_vault

    assert chakra_vault.__name__ == "chakra_vault"


def test_cli_module_imports() -> None:
    import chakra_vault.cli

    assert chakra_vault.cli.__name__ == "chakra_vault.cli"


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


def test_provider_modules_import() -> None:
    import chakra_vault.providers.huggingface
    import chakra_vault.providers.huggingface_download

    assert (
        chakra_vault.providers.huggingface.__name__
        == "chakra_vault.providers.huggingface"
    )
    assert (
        chakra_vault.providers.huggingface_download.__name__
        == "chakra_vault.providers.huggingface_download"
    )


def test_planner_modules_import() -> None:
    import chakra_vault.planner.download_plan

    assert chakra_vault.planner.download_plan.__name__ == "chakra_vault.planner.download_plan"


def test_downloader_modules_import() -> None:
    import chakra_vault.downloader.executor

    assert chakra_vault.downloader.executor.__name__ == "chakra_vault.downloader.executor"


def test_workflow_modules_import() -> None:
    import chakra_vault.workflows.model_download

    assert (
        chakra_vault.workflows.model_download.__name__
        == "chakra_vault.workflows.model_download"
    )
