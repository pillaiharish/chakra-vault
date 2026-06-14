"""Provider-neutral download planning."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from chakra_vault.verify import RemoteFileMetadata, normalize_remote_path, verify_files
from chakra_vault.verify.types import FileVerificationResult, VerificationStatus


class DownloadPlanAction(StrEnum):
    """Actions a future downloader or reporter can take."""

    SKIP_VERIFIED = "SKIP_VERIFIED"
    DOWNLOAD_MISSING = "DOWNLOAD_MISSING"
    REDOWNLOAD_CORRUPT = "REDOWNLOAD_CORRUPT"
    KEEP_UNVERIFIED = "KEEP_UNVERIFIED"
    REPORT_EXTRA_LOCAL = "REPORT_EXTRA_LOCAL"
    REPORT_REMOTE_METADATA_MISSING = "REPORT_REMOTE_METADATA_MISSING"


@dataclass(frozen=True)
class DownloadPlanItem:
    """One provider-neutral planning decision."""

    path: str
    action: DownloadPlanAction
    reason: str
    expected_size_bytes: int | None
    actual_size_bytes: int | None
    expected_sha256: str | None
    actual_sha256: str | None
    etag: str | None
    is_lfs: bool | None


@dataclass(frozen=True)
class DownloadPlan:
    """Typed manifest of planned download decisions."""

    items: tuple[DownloadPlanItem, ...]
    download_count: int
    redownload_count: int
    skip_count: int
    unverified_count: int
    extra_count: int
    metadata_missing_count: int
    planned_download_bytes: int | None


def build_download_plan(
    root: Path, expected_files: Sequence[RemoteFileMetadata]
) -> DownloadPlan:
    """Build a manifest describing what a future downloader should do."""

    expected_list = list(expected_files)
    expected_by_path = _expected_metadata_by_path(expected_list)
    verification = verify_files(root, expected_list)

    expected_items: list[DownloadPlanItem] = []
    extra_items: list[DownloadPlanItem] = []
    for result in verification.files:
        item = _plan_item(result, expected_by_path.get(result.path))
        if item.action is DownloadPlanAction.REPORT_EXTRA_LOCAL:
            extra_items.append(item)
        else:
            expected_items.append(item)

    items = tuple(expected_items + sorted(extra_items, key=lambda item: item.path))
    return DownloadPlan(
        items=items,
        download_count=_count(items, DownloadPlanAction.DOWNLOAD_MISSING),
        redownload_count=_count(items, DownloadPlanAction.REDOWNLOAD_CORRUPT),
        skip_count=_count(items, DownloadPlanAction.SKIP_VERIFIED),
        unverified_count=_count(items, DownloadPlanAction.KEEP_UNVERIFIED),
        extra_count=_count(items, DownloadPlanAction.REPORT_EXTRA_LOCAL),
        metadata_missing_count=_count(
            items, DownloadPlanAction.REPORT_REMOTE_METADATA_MISSING
        ),
        planned_download_bytes=_planned_download_bytes(items),
    )


def _expected_metadata_by_path(
    expected_files: Sequence[RemoteFileMetadata],
) -> dict[str, RemoteFileMetadata]:
    expected_by_path: dict[str, RemoteFileMetadata] = {}
    for expected_file in expected_files:
        path = normalize_remote_path(expected_file.path)
        if path in expected_by_path:
            raise ValueError("duplicate remote path")
        expected_by_path[path] = expected_file
    return expected_by_path


def _plan_item(
    result: FileVerificationResult,
    expected_file: RemoteFileMetadata | None,
) -> DownloadPlanItem:
    return DownloadPlanItem(
        path=result.path,
        action=_action_for_status(result.status),
        reason=result.message,
        expected_size_bytes=result.expected_size_bytes,
        actual_size_bytes=result.actual_size_bytes,
        expected_sha256=result.expected_sha256,
        actual_sha256=result.actual_sha256,
        etag=expected_file.etag if expected_file is not None else None,
        is_lfs=expected_file.is_lfs if expected_file is not None else None,
    )


def _action_for_status(status: VerificationStatus) -> DownloadPlanAction:
    if status is VerificationStatus.MATCH_PINNED:
        return DownloadPlanAction.SKIP_VERIFIED
    if status is VerificationStatus.LOCAL_MISSING_FILE:
        return DownloadPlanAction.DOWNLOAD_MISSING
    if status is VerificationStatus.LOCAL_CORRUPT:
        return DownloadPlanAction.REDOWNLOAD_CORRUPT
    if status is VerificationStatus.UNVERIFIED:
        return DownloadPlanAction.KEEP_UNVERIFIED
    if status is VerificationStatus.LOCAL_EXTRA_FILE:
        return DownloadPlanAction.REPORT_EXTRA_LOCAL
    if status is VerificationStatus.REMOTE_METADATA_MISSING:
        return DownloadPlanAction.REPORT_REMOTE_METADATA_MISSING
    raise ValueError("unsupported verification status")


def _count(items: tuple[DownloadPlanItem, ...], action: DownloadPlanAction) -> int:
    return sum(1 for item in items if item.action is action)


def _planned_download_bytes(items: tuple[DownloadPlanItem, ...]) -> int | None:
    planned_items = [
        item
        for item in items
        if item.action
        in {
            DownloadPlanAction.DOWNLOAD_MISSING,
            DownloadPlanAction.REDOWNLOAD_CORRUPT,
        }
    ]
    if not planned_items:
        return 0
    if any(item.expected_size_bytes is None for item in planned_items):
        return None
    return sum(item.expected_size_bytes for item in planned_items if item.expected_size_bytes)
