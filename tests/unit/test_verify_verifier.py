from __future__ import annotations

import hashlib

from chakra_vault.verify.types import RemoteFileMetadata, VerificationStatus
from chakra_vault.verify.verifier import collect_local_files, verify_files


def _write(tmp_path, relative_path: str, content: bytes):
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _remote(
    path: str,
    *,
    content: bytes | None = None,
    size_bytes: int | None = None,
    lfs_sha256: str | None = None,
    is_lfs: bool = True,
    etag: str | None = None,
) -> RemoteFileMetadata:
    return RemoteFileMetadata(
        path=path,
        size_bytes=len(content) if content is not None else size_bytes,
        etag=etag,
        lfs_sha256=_sha256(content) if content is not None else lfs_sha256,
        is_lfs=is_lfs,
    )


def test_collect_local_files_uses_relative_posix_paths(tmp_path) -> None:
    content = b"abc"
    _write(tmp_path, "nested/file.txt", content)

    files = collect_local_files(tmp_path)

    assert files["nested/file.txt"].path == "nested/file.txt"
    assert files["nested/file.txt"].size_bytes == len(content)
    assert files["nested/file.txt"].sha256 == _sha256(content)


def test_lfs_file_with_matching_sha_returns_match_pinned(tmp_path) -> None:
    content = b"weights metadata only"
    _write(tmp_path, "model.safetensors", content)

    result = verify_files(tmp_path, [_remote("model.safetensors", content=content)])

    assert result.status is VerificationStatus.MATCH_PINNED
    assert result.files[0].status is VerificationStatus.MATCH_PINNED
    assert result.matched_count == 1


def test_lfs_file_with_hash_mismatch_returns_corrupt(tmp_path) -> None:
    _write(tmp_path, "model.bin", b"actual")

    result = verify_files(
        tmp_path,
        [_remote("model.bin", size_bytes=6, lfs_sha256=_sha256(b"expect"))],
    )

    assert result.status is VerificationStatus.LOCAL_CORRUPT
    assert result.files[0].status is VerificationStatus.LOCAL_CORRUPT
    assert result.corrupt_count == 1


def test_size_mismatch_returns_corrupt(tmp_path) -> None:
    _write(tmp_path, "model.bin", b"actual")

    result = verify_files(
        tmp_path,
        [_remote("model.bin", size_bytes=100, lfs_sha256=_sha256(b"actual"))],
    )

    assert result.status is VerificationStatus.LOCAL_CORRUPT
    assert result.files[0].status is VerificationStatus.LOCAL_CORRUPT


def test_missing_expected_file_returns_missing(tmp_path) -> None:
    result = verify_files(
        tmp_path,
        [_remote("missing.bin", size_bytes=10, lfs_sha256=_sha256(b"missing"))],
    )

    assert result.status is VerificationStatus.LOCAL_MISSING_FILE
    assert result.files[0].status is VerificationStatus.LOCAL_MISSING_FILE
    assert result.missing_count == 1


def test_extra_local_file_returns_extra(tmp_path) -> None:
    content = b"extra"
    _write(tmp_path, "expected.bin", content)
    _write(tmp_path, "extra.bin", b"extra")

    result = verify_files(tmp_path, [_remote("expected.bin", content=content)])

    assert result.status is VerificationStatus.LOCAL_EXTRA_FILE
    assert result.extra_count == 1
    assert {file.status for file in result.files} == {
        VerificationStatus.MATCH_PINNED,
        VerificationStatus.LOCAL_EXTRA_FILE,
    }


def test_non_lfs_git_etag_is_unverified_not_corrupt(tmp_path) -> None:
    content = b"readme"
    _write(tmp_path, "README.md", content)

    result = verify_files(
        tmp_path,
        [
            _remote(
                "README.md",
                size_bytes=len(content),
                lfs_sha256=None,
                is_lfs=False,
                etag="git-style-etag",
            )
        ],
    )

    assert result.status is VerificationStatus.UNVERIFIED
    assert result.files[0].status is VerificationStatus.UNVERIFIED
    assert result.corrupt_count == 0
    assert result.unverified_count == 1


def test_lfs_metadata_missing_hash_returns_remote_metadata_missing(tmp_path) -> None:
    content = b"file"
    _write(tmp_path, "file.bin", content)

    result = verify_files(
        tmp_path,
        [_remote("file.bin", size_bytes=len(content), lfs_sha256=None)],
    )

    assert result.status is VerificationStatus.REMOTE_METADATA_MISSING
    assert result.files[0].status is VerificationStatus.REMOTE_METADATA_MISSING


def test_mixed_model_result_counts_are_correct(tmp_path) -> None:
    matched = b"matched"
    corrupt = b"corrupt"
    docs = b"docs"
    _write(tmp_path, "matched.bin", matched)
    _write(tmp_path, "corrupt.bin", corrupt)
    _write(tmp_path, "docs.md", docs)
    _write(tmp_path, "extra.bin", b"extra")

    result = verify_files(
        tmp_path,
        [
            _remote("matched.bin", content=matched),
            _remote("corrupt.bin", size_bytes=len(corrupt), lfs_sha256=_sha256(b"wrong")),
            _remote("missing.bin", size_bytes=7, lfs_sha256=_sha256(b"missing")),
            _remote(
                "docs.md",
                size_bytes=len(docs),
                lfs_sha256=None,
                is_lfs=False,
                etag="git-style-etag",
            ),
        ],
    )

    assert result.status is VerificationStatus.LOCAL_CORRUPT
    assert result.matched_count == 1
    assert result.missing_count == 1
    assert result.corrupt_count == 1
    assert result.extra_count == 1
    assert result.unverified_count == 1


def test_empty_expected_metadata_is_not_pinned_success(tmp_path) -> None:
    result = verify_files(tmp_path, [])

    assert result.status is VerificationStatus.REMOTE_METADATA_MISSING
