"""Local hash and verification primitives."""

from chakra_vault.verify.hasher import (
    FileHashError,
    FileIsDirectoryError,
    FileIsSymlinkError,
    FileMissingError,
    FileUnreadableError,
    sha256_file,
)
from chakra_vault.verify.types import (
    FileVerificationResult,
    LocalFileMetadata,
    ModelVerificationResult,
    RemoteFileMetadata,
    VerificationStatus,
)
from chakra_vault.verify.verifier import collect_local_files, verify_files

__all__ = [
    "FileHashError",
    "FileIsDirectoryError",
    "FileIsSymlinkError",
    "FileMissingError",
    "FileUnreadableError",
    "FileVerificationResult",
    "LocalFileMetadata",
    "ModelVerificationResult",
    "RemoteFileMetadata",
    "VerificationStatus",
    "collect_local_files",
    "sha256_file",
    "verify_files",
]
