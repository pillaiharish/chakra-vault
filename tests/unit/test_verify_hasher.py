from __future__ import annotations

import hashlib
import os
import stat

import pytest

from chakra_vault.verify.hasher import (
    FileIsDirectoryError,
    FileIsSymlinkError,
    FileMissingError,
    FileUnreadableError,
    sha256_file,
)


def test_sha256_file_hashes_known_content(tmp_path) -> None:
    path = tmp_path / "tiny.txt"
    content = b"chakra-vault\n"
    path.write_bytes(content)

    assert sha256_file(path, chunk_size=4) == hashlib.sha256(content).hexdigest()


def test_sha256_file_missing_file_raises_clear_error(tmp_path) -> None:
    missing_path = tmp_path / "missing.bin"

    with pytest.raises(FileMissingError, match="file does not exist") as error:
        sha256_file(missing_path)

    assert str(tmp_path) not in str(error.value)


def test_sha256_file_directory_raises_clear_error(tmp_path) -> None:
    with pytest.raises(FileIsDirectoryError, match="path is a directory") as error:
        sha256_file(tmp_path)

    assert str(tmp_path) not in str(error.value)


def test_sha256_file_rejects_symlink_without_hashing_target(tmp_path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("target content", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("current platform cannot create symlinks")

    with pytest.raises(FileIsSymlinkError, match="path is a symlink") as error:
        sha256_file(link)

    assert str(tmp_path) not in str(error.value)


def test_sha256_file_unreadable_file_raises_clear_error(tmp_path) -> None:
    path = tmp_path / "locked.txt"
    path.write_text("locked", encoding="utf-8")
    original_mode = stat.S_IMODE(path.stat().st_mode)

    try:
        path.chmod(0)
        if os.access(path, os.R_OK):
            pytest.skip("current platform can still read chmod 0 files")
        with pytest.raises(FileUnreadableError, match="file could not be read") as error:
            sha256_file(path)
        assert str(tmp_path) not in str(error.value)
    finally:
        path.chmod(original_mode)


def test_sha256_file_rejects_invalid_chunk_size(tmp_path) -> None:
    path = tmp_path / "tiny.txt"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="chunk_size"):
        sha256_file(path, chunk_size=0)
