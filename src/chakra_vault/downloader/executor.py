"""Safe provider-neutral download execution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO, Protocol

from chakra_vault.planner import DownloadPlan, DownloadPlanAction, DownloadPlanItem
from chakra_vault.verify import normalize_remote_path
from chakra_vault.verify.hasher import sha256_file


class DownloadExecutionStatus(StrEnum):
    """Possible execution outcomes for a plan item."""

    DOWNLOADED = "DOWNLOADED"
    REDOWNLOADED = "REDOWNLOADED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DownloadExecutionResult:
    """Execution result for one download plan item."""

    path: str
    status: DownloadExecutionStatus
    bytes_written: int
    message: str


@dataclass(frozen=True)
class DownloadExecutionSummary:
    """Execution summary for a download plan."""

    results: tuple[DownloadExecutionResult, ...]
    downloaded_count: int
    redownloaded_count: int
    skipped_count: int
    failed_count: int
    bytes_written: int


class DownloadSource(Protocol):
    """Provider-neutral source of bytes for a plan item path."""

    def open(self, path: str) -> BinaryIO:
        """Open a readable binary stream for ``path``."""


def execute_download_plan(
    root: Path,
    plan: DownloadPlan,
    source: DownloadSource,
    *,
    chunk_size: int = 1024 * 1024,
) -> DownloadExecutionSummary:
    """Execute download and redownload actions from a plan."""

    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")

    results = tuple(
        _execute_item(root, item, source, chunk_size=chunk_size) for item in plan.items
    )
    return DownloadExecutionSummary(
        results=results,
        downloaded_count=_count(results, DownloadExecutionStatus.DOWNLOADED),
        redownloaded_count=_count(results, DownloadExecutionStatus.REDOWNLOADED),
        skipped_count=_count(results, DownloadExecutionStatus.SKIPPED),
        failed_count=_count(results, DownloadExecutionStatus.FAILED),
        bytes_written=sum(result.bytes_written for result in results),
    )


def _execute_item(
    root: Path,
    item: DownloadPlanItem,
    source: DownloadSource,
    *,
    chunk_size: int,
) -> DownloadExecutionResult:
    try:
        path = normalize_remote_path(item.path)
    except ValueError:
        return _failed(item.path, "plan item path is unsafe")

    if item.action not in {
        DownloadPlanAction.DOWNLOAD_MISSING,
        DownloadPlanAction.REDOWNLOAD_CORRUPT,
    }:
        return DownloadExecutionResult(
            path=path,
            status=DownloadExecutionStatus.SKIPPED,
            bytes_written=0,
            message="plan item does not require download",
        )

    try:
        return _execute_download_item(root, path, item, source, chunk_size=chunk_size)
    except Exception:
        return _failed(path, "download execution failed")


def _execute_download_item(
    root: Path,
    path: str,
    item: DownloadPlanItem,
    source: DownloadSource,
    *,
    chunk_size: int,
) -> DownloadExecutionResult:
    final_path = _safe_final_path(root, path)
    part_path = final_path.with_name(f"{final_path.name}.part")

    _prepare_parent(root, final_path.parent)
    _check_parent(root, final_path.parent)
    _reject_symlink(final_path, "final file is unsafe")
    _reject_symlink(part_path, "temporary file is unsafe")

    if item.action is DownloadPlanAction.DOWNLOAD_MISSING and final_path.exists():
        return _failed(path, "final file already exists")

    bytes_written = 0
    try:
        _check_parent(root, final_path.parent)
        with _create_part_file(part_path) as target:
            with source.open(path) as stream:
                while True:
                    chunk = stream.read(chunk_size)
                    if not chunk:
                        break
                    target.write(chunk)
                    bytes_written += len(chunk)
        _verify_part_file(part_path, item)
        part_path.replace(final_path)
    except Exception:
        _remove_file(part_path)
        raise

    status = (
        DownloadExecutionStatus.REDOWNLOADED
        if item.action is DownloadPlanAction.REDOWNLOAD_CORRUPT
        else DownloadExecutionStatus.DOWNLOADED
    )
    return DownloadExecutionResult(
        path=path,
        status=status,
        bytes_written=bytes_written,
        message="download completed",
    )


def _safe_final_path(root: Path, path: str) -> Path:
    if root.is_symlink():
        raise ValueError("download root is unsafe")
    root.mkdir(parents=True, exist_ok=True)
    return root / path


def _prepare_parent(root: Path, parent: Path) -> None:
    _check_parent(root, parent)
    parent.mkdir(parents=True, exist_ok=True)
    _check_parent(root, parent)


def _check_parent(root: Path, parent: Path) -> None:
    for existing_parent in _existing_parents(root, parent):
        if existing_parent.is_symlink():
            raise ValueError("parent path is unsafe")
        if existing_parent.exists() and not existing_parent.is_dir():
            raise ValueError("parent path is unsafe")


def _existing_parents(root: Path, parent: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    current = parent
    while current != root and current != current.parent:
        paths.append(current)
        current = current.parent
    paths.append(root)
    return tuple(reversed(paths))


def _verify_part_file(path: Path, item: DownloadPlanItem) -> None:
    if item.expected_size_bytes is not None and path.stat().st_size != item.expected_size_bytes:
        raise ValueError("downloaded file size mismatch")
    if item.expected_sha256 is not None and sha256_file(path) != item.expected_sha256:
        raise ValueError("downloaded file hash mismatch")


def _create_part_file(path: Path) -> BinaryIO:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        return os.fdopen(fd, "wb")
    except Exception:
        os.close(fd)
        raise


def _reject_symlink(path: Path, message: str) -> None:
    if path.is_symlink():
        raise ValueError(message)


def _remove_file(path: Path) -> None:
    try:
        if path.exists() or path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _failed(path: str, message: str) -> DownloadExecutionResult:
    return DownloadExecutionResult(
        path=path,
        status=DownloadExecutionStatus.FAILED,
        bytes_written=0,
        message=message,
    )


def _count(
    results: tuple[DownloadExecutionResult, ...],
    status: DownloadExecutionStatus,
) -> int:
    return sum(1 for result in results if result.status is status)
