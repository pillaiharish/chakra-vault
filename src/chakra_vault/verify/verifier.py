"""Local verification against provider-neutral file metadata."""

from __future__ import annotations

from pathlib import Path

from chakra_vault.verify.hasher import sha256_file
from chakra_vault.verify.types import (
    FileVerificationResult,
    LocalFileMetadata,
    ModelVerificationResult,
    RemoteFileMetadata,
    VerificationStatus,
)


def collect_local_files(root: Path) -> dict[str, LocalFileMetadata]:
    """Collect local regular files below ``root`` keyed by relative POSIX path."""

    if not root.exists():
        raise FileNotFoundError("verification root does not exist")
    if not root.is_dir():
        raise NotADirectoryError("verification root must be a directory")

    local_files: dict[str, LocalFileMetadata] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = _relative_path(root, path)
        local_files[relative_path] = LocalFileMetadata(
            path=relative_path,
            size_bytes=path.stat().st_size,
            sha256=sha256_file(path),
        )
    return local_files


def verify_files(
    root: Path, expected_files: list[RemoteFileMetadata]
) -> ModelVerificationResult:
    """Verify local files under ``root`` against expected metadata."""

    local_files = collect_local_files(root)
    results: list[FileVerificationResult] = []
    expected_paths = {_normalize_remote_path(file.path) for file in expected_files}

    for expected_file in expected_files:
        expected_path = _normalize_remote_path(expected_file.path)
        local_file = local_files.get(expected_path)
        if local_file is None:
            results.append(
                FileVerificationResult(
                    path=expected_path,
                    status=VerificationStatus.LOCAL_MISSING_FILE,
                    expected_size_bytes=expected_file.size_bytes,
                    actual_size_bytes=None,
                    expected_sha256=expected_file.lfs_sha256,
                    actual_sha256=None,
                    message="expected file is missing locally",
                )
            )
            continue

        results.append(_verify_one(expected_file, expected_path, local_file))

    for path, local_file in local_files.items():
        if path not in expected_paths:
            results.append(
                FileVerificationResult(
                    path=path,
                    status=VerificationStatus.LOCAL_EXTRA_FILE,
                    expected_size_bytes=None,
                    actual_size_bytes=local_file.size_bytes,
                    expected_sha256=None,
                    actual_sha256=local_file.sha256,
                    message="local file is not present in expected metadata",
                )
            )

    return _model_result(tuple(results), has_expected_metadata=bool(expected_files))


def _verify_one(
    expected_file: RemoteFileMetadata,
    expected_path: str,
    local_file: LocalFileMetadata,
) -> FileVerificationResult:
    if (
        expected_file.size_bytes is not None
        and expected_file.size_bytes != local_file.size_bytes
    ):
        return FileVerificationResult(
            path=expected_path,
            status=VerificationStatus.LOCAL_CORRUPT,
            expected_size_bytes=expected_file.size_bytes,
            actual_size_bytes=local_file.size_bytes,
            expected_sha256=expected_file.lfs_sha256,
            actual_sha256=local_file.sha256,
            message="local file size does not match expected metadata",
        )

    if expected_file.is_lfs:
        if expected_file.lfs_sha256 is None:
            return FileVerificationResult(
                path=expected_path,
                status=VerificationStatus.REMOTE_METADATA_MISSING,
                expected_size_bytes=expected_file.size_bytes,
                actual_size_bytes=local_file.size_bytes,
                expected_sha256=None,
                actual_sha256=local_file.sha256,
                message="expected LFS metadata is missing a SHA-256 value",
            )
        if expected_file.lfs_sha256 != local_file.sha256:
            return FileVerificationResult(
                path=expected_path,
                status=VerificationStatus.LOCAL_CORRUPT,
                expected_size_bytes=expected_file.size_bytes,
                actual_size_bytes=local_file.size_bytes,
                expected_sha256=expected_file.lfs_sha256,
                actual_sha256=local_file.sha256,
                message="local file hash does not match expected LFS SHA-256",
            )
        return FileVerificationResult(
            path=expected_path,
            status=VerificationStatus.MATCH_PINNED,
            expected_size_bytes=expected_file.size_bytes,
            actual_size_bytes=local_file.size_bytes,
            expected_sha256=expected_file.lfs_sha256,
            actual_sha256=local_file.sha256,
            message="local file matches expected pinned LFS metadata",
        )

    return FileVerificationResult(
        path=expected_path,
        status=VerificationStatus.UNVERIFIED,
        expected_size_bytes=expected_file.size_bytes,
        actual_size_bytes=local_file.size_bytes,
        expected_sha256=None,
        actual_sha256=local_file.sha256,
        message="non-LFS file has no pinned SHA-256 metadata",
    )


def _model_result(
    files: tuple[FileVerificationResult, ...],
    *,
    has_expected_metadata: bool,
) -> ModelVerificationResult:
    matched_count = _count(files, VerificationStatus.MATCH_PINNED)
    missing_count = _count(files, VerificationStatus.LOCAL_MISSING_FILE)
    corrupt_count = _count(files, VerificationStatus.LOCAL_CORRUPT)
    extra_count = _count(files, VerificationStatus.LOCAL_EXTRA_FILE)
    unverified_count = _count(files, VerificationStatus.UNVERIFIED)
    remote_metadata_missing_count = _count(
        files, VerificationStatus.REMOTE_METADATA_MISSING
    )

    if corrupt_count:
        status = VerificationStatus.LOCAL_CORRUPT
    elif missing_count:
        status = VerificationStatus.LOCAL_MISSING_FILE
    elif extra_count:
        status = VerificationStatus.LOCAL_EXTRA_FILE
    elif remote_metadata_missing_count or not has_expected_metadata:
        status = VerificationStatus.REMOTE_METADATA_MISSING
    elif unverified_count:
        status = VerificationStatus.UNVERIFIED
    else:
        status = VerificationStatus.MATCH_PINNED

    return ModelVerificationResult(
        status=status,
        files=files,
        matched_count=matched_count,
        missing_count=missing_count,
        corrupt_count=corrupt_count,
        extra_count=extra_count,
        unverified_count=unverified_count,
    )


def _count(
    files: tuple[FileVerificationResult, ...], status: VerificationStatus
) -> int:
    return sum(1 for file in files if file.status is status)


def _normalize_remote_path(path: str) -> str:
    return Path(path).as_posix().lstrip("/")


def _relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
