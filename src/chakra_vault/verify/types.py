"""Verification result types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class RemoteFileMetadata:
    """Expected file metadata from a remote provider."""

    path: str
    size_bytes: int | None
    etag: str | None
    lfs_sha256: str | None
    is_lfs: bool


@dataclass(frozen=True)
class LocalFileMetadata:
    """Observed local file metadata."""

    path: str
    size_bytes: int
    sha256: str


class VerificationStatus(StrEnum):
    """Possible verification statuses."""

    MATCH_PINNED = "MATCH_PINNED"
    LOCAL_CORRUPT = "LOCAL_CORRUPT"
    LOCAL_MISSING_FILE = "LOCAL_MISSING_FILE"
    LOCAL_EXTRA_FILE = "LOCAL_EXTRA_FILE"
    REMOTE_METADATA_MISSING = "REMOTE_METADATA_MISSING"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class FileVerificationResult:
    """Verification result for one path."""

    path: str
    status: VerificationStatus
    expected_size_bytes: int | None
    actual_size_bytes: int | None
    expected_sha256: str | None
    actual_sha256: str | None
    message: str


@dataclass(frozen=True)
class ModelVerificationResult:
    """Verification result for a group of files."""

    status: VerificationStatus
    files: tuple[FileVerificationResult, ...]
    matched_count: int
    missing_count: int
    corrupt_count: int
    extra_count: int
    unverified_count: int
