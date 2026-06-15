"""Read-only Hugging Face download source."""

from __future__ import annotations

from typing import BinaryIO

from chakra_vault.verify import normalize_remote_path


class HuggingFaceDownloadSourceError(RuntimeError):
    """Raised when a Hugging Face file cannot be opened for reading."""


class HuggingFaceDownloadSource:
    """Open Hugging Face model files through a filesystem-like reader."""

    def __init__(
        self,
        repo_id: str,
        *,
        revision: str | None = None,
        token: str | bool | None = None,
        filesystem: object | None = None,
    ) -> None:
        self._repo_id = repo_id
        self._revision = revision
        self._token = token
        self._filesystem = filesystem

    def open(self, path: str) -> BinaryIO:
        """Open a remote provider path as a readable binary stream."""

        normalized_path = normalize_remote_path(path)
        remote_path = self._remote_path(normalized_path)
        filesystem = (
            self._filesystem
            if self._filesystem is not None
            else _build_filesystem(self._token)
        )
        try:
            return filesystem.open(remote_path, "rb")
        except Exception as error:
            raise HuggingFaceDownloadSourceError("failed to open Hugging Face file") from error

    def _remote_path(self, path: str) -> str:
        if self._revision is None:
            return f"{self._repo_id}/{path}"
        return f"{self._repo_id}@{self._revision}/{path}"


def _build_filesystem(token: str | bool | None) -> object:
    try:
        from huggingface_hub import HfFileSystem
    except ImportError as error:
        raise HuggingFaceDownloadSourceError("failed to open Hugging Face file") from error
    try:
        return HfFileSystem(token=token)
    except Exception as error:
        raise HuggingFaceDownloadSourceError("failed to open Hugging Face file") from error
