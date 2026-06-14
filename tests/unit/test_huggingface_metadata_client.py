from __future__ import annotations

from types import SimpleNamespace

import pytest

from chakra_vault.providers.huggingface import (
    HuggingFaceMetadataClient,
    HuggingFaceMetadataError,
)


class FakeApi:
    def __init__(self, model_info: object | None = None, error: Exception | None = None) -> None:
        self.model_info_result = model_info
        self.error = error
        self.calls: list[dict[str, object]] = []

    def model_info(
        self,
        *,
        repo_id: str,
        revision: str | None,
        files_metadata: bool,
    ) -> object:
        self.calls.append(
            {
                "repo_id": repo_id,
                "revision": revision,
                "files_metadata": files_metadata,
            }
        )
        if self.error is not None:
            raise self.error
        return self.model_info_result


def test_client_calls_model_info_with_files_metadata() -> None:
    api = FakeApi(SimpleNamespace(siblings=[]))
    client = HuggingFaceMetadataClient(api=api)

    assert client.list_model_files("org/model") == ()
    assert api.calls == [
        {
            "repo_id": "org/model",
            "revision": None,
            "files_metadata": True,
        }
    ]


def test_client_passes_revision_through() -> None:
    api = FakeApi(SimpleNamespace(siblings=[]))
    client = HuggingFaceMetadataClient(api=api)

    client.list_model_files("org/model", revision="main")

    assert api.calls[0]["revision"] == "main"


def test_object_style_lfs_sibling_converts_to_remote_metadata() -> None:
    sibling = SimpleNamespace(
        rfilename="model.safetensors",
        size=123,
        blob_id="blob-sha",
        lfs=SimpleNamespace(sha256="lfs-sha"),
    )
    client = HuggingFaceMetadataClient(api=FakeApi(SimpleNamespace(siblings=[sibling])))

    (metadata,) = client.list_model_files("org/model")

    assert metadata.path == "model.safetensors"
    assert metadata.size_bytes == 123
    assert metadata.etag == "blob-sha"
    assert metadata.is_lfs is True
    assert metadata.lfs_sha256 == "lfs-sha"


def test_dict_style_lfs_sibling_converts_to_remote_metadata() -> None:
    sibling = {
        "rfilename": "model.bin",
        "size": 456,
        "etag": "etag-sha",
        "lfs": {"sha256": "dict-lfs-sha"},
    }
    client = HuggingFaceMetadataClient(api=FakeApi({"siblings": [sibling]}))

    (metadata,) = client.list_model_files("org/model")

    assert metadata.path == "model.bin"
    assert metadata.size_bytes == 456
    assert metadata.etag == "etag-sha"
    assert metadata.is_lfs is True
    assert metadata.lfs_sha256 == "dict-lfs-sha"


def test_non_lfs_sibling_preserves_blob_id_without_lfs_sha() -> None:
    sibling = SimpleNamespace(
        rfilename="README.md",
        size=12,
        blob_id="git-blob-id",
        lfs=None,
    )
    client = HuggingFaceMetadataClient(api=FakeApi(SimpleNamespace(siblings=[sibling])))

    (metadata,) = client.list_model_files("org/model")

    assert metadata.path == "README.md"
    assert metadata.size_bytes == 12
    assert metadata.etag == "git-blob-id"
    assert metadata.is_lfs is False
    assert metadata.lfs_sha256 is None


def test_nested_provider_path_is_allowed() -> None:
    sibling = SimpleNamespace(
        rfilename="nested/tokenizer.json",
        size=7,
        blob_id="blob",
        lfs=None,
    )
    client = HuggingFaceMetadataClient(api=FakeApi(SimpleNamespace(siblings=[sibling])))

    (metadata,) = client.list_model_files("org/model")

    assert metadata.path == "nested/tokenizer.json"


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.bin",
        "/tmp/outside.bin",
        "nested\\..\\outside.bin",
        "",
        ".",
        "C:\\tmp\\outside.bin",
    ],
)
def test_unsafe_sibling_paths_are_rejected(unsafe_path: str) -> None:
    sibling = SimpleNamespace(rfilename=unsafe_path, size=1, blob_id="blob", lfs=None)
    client = HuggingFaceMetadataClient(api=FakeApi(SimpleNamespace(siblings=[sibling])))

    with pytest.raises(ValueError, match="remote path is unsafe"):
        client.list_model_files("org/model")


def test_empty_siblings_returns_empty_tuple() -> None:
    client = HuggingFaceMetadataClient(api=FakeApi(SimpleNamespace(siblings=[])))

    assert client.list_model_files("org/model") == ()


def test_missing_siblings_returns_empty_tuple() -> None:
    client = HuggingFaceMetadataClient(api=FakeApi(SimpleNamespace()))

    assert client.list_model_files("org/model") == ()


def test_provider_error_message_is_generic() -> None:
    api = FakeApi(error=RuntimeError("token-secret at /tmp/local-file"))
    client = HuggingFaceMetadataClient(api=api)

    with pytest.raises(HuggingFaceMetadataError) as error:
        client.list_model_files("org/model")

    message = str(error.value)
    assert message == "failed to read Hugging Face model metadata"
    assert "token-secret" not in message
    assert "/tmp/local-file" not in message
