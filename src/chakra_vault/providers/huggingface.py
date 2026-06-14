"""Read-only Hugging Face metadata client."""

from __future__ import annotations

from collections.abc import Mapping

from chakra_vault.verify import RemoteFileMetadata, normalize_remote_path


class HuggingFaceMetadataError(RuntimeError):
    """Raised when Hugging Face metadata cannot be read."""


class HuggingFaceMetadataClient:
    """Fetch read-only Hugging Face model file metadata."""

    def __init__(self, api: object | None = None) -> None:
        self._api = api

    def list_model_files(
        self, repo_id: str, revision: str | None = None
    ) -> tuple[RemoteFileMetadata, ...]:
        api = self._api if self._api is not None else _build_hf_api()
        try:
            model_info = api.model_info(
                repo_id=repo_id,
                revision=revision,
                files_metadata=True,
            )
        except Exception as error:
            raise HuggingFaceMetadataError(
                "failed to read Hugging Face model metadata"
            ) from error

        siblings = _get_value(model_info, "siblings")
        if not siblings:
            return ()

        return tuple(_remote_file_from_sibling(sibling) for sibling in siblings)


def _build_hf_api() -> object:
    try:
        from huggingface_hub import HfApi
    except ImportError as error:
        raise HuggingFaceMetadataError(
            "huggingface-hub is required for Hugging Face metadata"
        ) from error
    return HfApi()


def _remote_file_from_sibling(sibling: object) -> RemoteFileMetadata:
    path = normalize_remote_path(_require_text(_get_value(sibling, "rfilename")))
    lfs_metadata = _get_value(sibling, "lfs")
    is_lfs = lfs_metadata is not None

    return RemoteFileMetadata(
        path=path,
        size_bytes=_optional_int(_get_value(sibling, "size")),
        etag=_optional_text(
            _first_present(
                _get_value(sibling, "blob_id"),
                _get_value(sibling, "etag"),
            )
        ),
        lfs_sha256=_optional_text(_get_value(lfs_metadata, "sha256")) if is_lfs else None,
        is_lfs=is_lfs,
    )


def _get_value(source: object, name: str) -> object | None:
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _first_present(*values: object | None) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None


def _require_text(value: object | None) -> str:
    if not isinstance(value, str):
        raise ValueError("remote path is unsafe")
    return value


def _optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _optional_int(value: object | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return int(value)
