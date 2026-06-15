from __future__ import annotations

import hashlib
import inspect
from io import BytesIO
from pathlib import Path

import pytest

import chakra_vault.workflows.model_download as workflow
from chakra_vault.downloader import DownloadExecutionStatus
from chakra_vault.planner import DownloadPlanAction
from chakra_vault.verify import RemoteFileMetadata, VerificationStatus
from chakra_vault.workflows import (
    ModelDownloadWorkflowError,
    ModelDownloadWorkflowResult,
    download_huggingface_model,
)


class FakeMetadataClient:
    def __init__(
        self,
        files: tuple[RemoteFileMetadata, ...],
        error: Exception | None = None,
    ) -> None:
        self.files = files
        self.error = error
        self.calls: list[tuple[str, str | None]] = []

    def list_model_files(
        self, repo_id: str, revision: str | None = None
    ) -> tuple[RemoteFileMetadata, ...]:
        self.calls.append((repo_id, revision))
        if self.error is not None:
            raise self.error
        return self.files


class FakeDownloadSource:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.calls: list[str] = []

    def open(self, path: str):
        self.calls.append(path)
        return BytesIO(self.files[path])


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _remote(path: str, content: bytes) -> RemoteFileMetadata:
    return RemoteFileMetadata(
        path=path,
        size_bytes=len(content),
        etag=None,
        lfs_sha256=_sha256(content),
        is_lfs=True,
    )


def test_workflow_downloads_missing_file_and_final_verification_matches(
    tmp_path: Path,
) -> None:
    content = b"model bytes"
    metadata = (_remote("model.bin", content),)
    metadata_client = FakeMetadataClient(metadata)
    source = FakeDownloadSource({"model.bin": content})

    result = download_huggingface_model(
        "org/model",
        tmp_path,
        revision="main",
        metadata_client=metadata_client,
        download_source=source,
    )

    assert isinstance(result, ModelDownloadWorkflowResult)
    assert result.repo_id == "org/model"
    assert result.revision == "main"
    assert metadata_client.calls == [("org/model", "main")]
    assert source.calls == ["model.bin"]
    assert result.plan.items[0].action is DownloadPlanAction.DOWNLOAD_MISSING
    assert result.execution.results[0].status is DownloadExecutionStatus.DOWNLOADED
    assert result.verification.status is VerificationStatus.MATCH_PINNED
    assert (tmp_path / "model.bin").read_bytes() == content


def test_existing_verified_file_is_skipped_and_source_is_not_called(tmp_path: Path) -> None:
    content = b"existing bytes"
    (tmp_path / "model.bin").write_bytes(content)
    metadata_client = FakeMetadataClient((_remote("model.bin", content),))
    source = FakeDownloadSource({"model.bin": b"unused"})

    result = download_huggingface_model(
        "org/model",
        tmp_path,
        metadata_client=metadata_client,
        download_source=source,
    )

    assert result.plan.items[0].action is DownloadPlanAction.SKIP_VERIFIED
    assert result.execution.results[0].status is DownloadExecutionStatus.SKIPPED
    assert result.verification.status is VerificationStatus.MATCH_PINNED
    assert source.calls == []


def test_corrupt_local_file_is_redownloaded_and_verified(tmp_path: Path) -> None:
    content = b"correct bytes"
    (tmp_path / "model.bin").write_bytes(b"corrupt")
    metadata_client = FakeMetadataClient((_remote("model.bin", content),))
    source = FakeDownloadSource({"model.bin": content})

    result = download_huggingface_model(
        "org/model",
        tmp_path,
        metadata_client=metadata_client,
        download_source=source,
    )

    assert result.plan.items[0].action is DownloadPlanAction.REDOWNLOAD_CORRUPT
    assert result.execution.results[0].status is DownloadExecutionStatus.REDOWNLOADED
    assert result.verification.status is VerificationStatus.MATCH_PINNED
    assert (tmp_path / "model.bin").read_bytes() == content


def test_default_source_construction_receives_repo_revision_and_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    content = b"model bytes"
    constructed: list[tuple[str, str | None, str | bool | None]] = []

    class FakeDefaultSource(FakeDownloadSource):
        def __init__(
            self,
            repo_id: str,
            *,
            revision: str | None = None,
            token: str | bool | None = None,
        ) -> None:
            constructed.append((repo_id, revision, token))
            super().__init__({"model.bin": content})

    monkeypatch.setattr(workflow, "HuggingFaceDownloadSource", FakeDefaultSource)

    result = download_huggingface_model(
        "org/model",
        tmp_path,
        revision="abc123",
        token="token-secret",
        metadata_client=FakeMetadataClient((_remote("model.bin", content),)),
    )

    assert constructed == [("org/model", "abc123", "token-secret")]
    assert result.verification.status is VerificationStatus.MATCH_PINNED


def test_workflow_returns_plan_execution_and_verification_objects(tmp_path: Path) -> None:
    content = b"model bytes"

    result = download_huggingface_model(
        "org/model",
        tmp_path,
        metadata_client=FakeMetadataClient((_remote("model.bin", content),)),
        download_source=FakeDownloadSource({"model.bin": content}),
    )

    assert result.plan.download_count == 1
    assert result.execution.downloaded_count == 1
    assert result.verification.matched_count == 1


def test_workflow_module_does_not_import_download_helpers_or_direct_network_clients() -> None:
    source = inspect.getsource(workflow)

    assert "hf_hub_download" not in source
    assert "snapshot_download" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "urllib" not in source


def test_workflow_module_does_not_perform_direct_local_writes() -> None:
    source = inspect.getsource(workflow)

    assert ".write_bytes" not in source
    assert ".write_text" not in source
    assert ".open(" not in source
    assert ".mkdir(" not in source
    assert ".replace(" not in source
    assert ".unlink(" not in source


def test_token_like_metadata_error_is_wrapped_without_leak(tmp_path: Path) -> None:
    metadata_client = FakeMetadataClient(
        (),
        error=RuntimeError(f"token-secret at https://huggingface.co from {tmp_path}"),
    )

    with pytest.raises(ModelDownloadWorkflowError) as error:
        download_huggingface_model(
            "org/model",
            tmp_path,
            token="token-secret",
            metadata_client=metadata_client,
            download_source=FakeDownloadSource({}),
        )

    message = str(error.value)
    assert message == "failed to fetch model metadata"
    assert "token-secret" not in message
    assert "https://huggingface.co" not in message
    assert str(tmp_path) not in message


def test_unsafe_metadata_path_is_rejected_by_lower_layer(tmp_path: Path) -> None:
    metadata_client = FakeMetadataClient(
        (
            RemoteFileMetadata(
                path="../outside.bin",
                size_bytes=1,
                etag=None,
                lfs_sha256="not-used",
                is_lfs=True,
            ),
        )
    )

    with pytest.raises(ValueError, match="remote path is unsafe"):
        download_huggingface_model(
            "org/model",
            tmp_path,
            metadata_client=metadata_client,
            download_source=FakeDownloadSource({"../outside.bin": b"x"}),
        )
