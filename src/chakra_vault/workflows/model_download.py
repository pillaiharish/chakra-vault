"""Model download workflow composition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chakra_vault.downloader import (
    DownloadExecutionSummary,
    DownloadSource,
    execute_download_plan,
)
from chakra_vault.planner import DownloadPlan, build_download_plan
from chakra_vault.providers import HuggingFaceDownloadSource, HuggingFaceMetadataClient
from chakra_vault.verify import ModelVerificationResult, verify_files


class ModelDownloadWorkflowError(RuntimeError):
    """Raised when model download workflow setup fails."""


@dataclass(frozen=True)
class ModelDownloadWorkflowResult:
    """Result of a model download workflow run."""

    repo_id: str
    revision: str | None
    plan: DownloadPlan
    execution: DownloadExecutionSummary
    verification: ModelVerificationResult


def download_huggingface_model(
    repo_id: str,
    root: Path,
    *,
    revision: str | None = None,
    token: str | bool | None = None,
    metadata_client: HuggingFaceMetadataClient | None = None,
    download_source: DownloadSource | None = None,
) -> ModelDownloadWorkflowResult:
    """Download a Hugging Face model by composing metadata, planning, and execution."""

    client = metadata_client if metadata_client is not None else HuggingFaceMetadataClient()
    source = (
        download_source
        if download_source is not None
        else _build_download_source(repo_id, revision=revision, token=token)
    )

    try:
        expected_files = client.list_model_files(repo_id, revision=revision)
    except ValueError:
        raise
    except Exception as error:
        raise ModelDownloadWorkflowError("failed to fetch model metadata") from error

    plan = build_download_plan(root, expected_files)
    execution = execute_download_plan(root, plan, source)
    verification = verify_files(root, list(expected_files))
    return ModelDownloadWorkflowResult(
        repo_id=repo_id,
        revision=revision,
        plan=plan,
        execution=execution,
        verification=verification,
    )


def _build_download_source(
    repo_id: str,
    *,
    revision: str | None,
    token: str | bool | None,
) -> DownloadSource:
    try:
        return HuggingFaceDownloadSource(repo_id, revision=revision, token=token)
    except Exception as error:
        raise ModelDownloadWorkflowError("failed to create download source") from error
