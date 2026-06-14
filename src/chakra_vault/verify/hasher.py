"""Local file hashing helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


class FileHashError(OSError):
    """Base error for local file hashing failures."""


class FileMissingError(FileHashError):
    """Raised when a requested file does not exist."""


class FileIsDirectoryError(FileHashError):
    """Raised when a directory is passed where a file is required."""


class FileIsSymlinkError(FileHashError):
    """Raised when a symlink is passed where a regular file is required."""


class FileUnreadableError(FileHashError):
    """Raised when a file cannot be read."""


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 hex digest for a local file."""

    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")

    if path.is_symlink():
        raise FileIsSymlinkError("path is a symlink, expected a regular file")
    if not path.exists():
        raise FileMissingError("file does not exist")
    if path.is_dir():
        raise FileIsDirectoryError("path is a directory, expected a file")
    if not path.is_file():
        raise FileUnreadableError("path is not a regular file")

    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(chunk_size), b""):
                digest.update(chunk)
    except OSError as error:
        raise FileUnreadableError("file could not be read") from error

    return digest.hexdigest()
