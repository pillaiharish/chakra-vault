from __future__ import annotations

import builtins
from io import BytesIO
from pathlib import Path

import pytest

from chakra_vault.providers.huggingface_download import (
    HuggingFaceDownloadSource,
    HuggingFaceDownloadSourceError,
)


class FakeFilesystem:
    def __init__(self, content: bytes = b"content", error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def open(self, path: str, mode: str):
        self.calls.append((path, mode))
        if self.error is not None:
            raise self.error
        return BytesIO(self.content)

    def hf_hub_download(self) -> None:
        raise AssertionError("hf_hub_download must not be called")

    def snapshot_download(self) -> None:
        raise AssertionError("snapshot_download must not be called")


def test_open_uses_expected_repo_path() -> None:
    filesystem = FakeFilesystem(b"model bytes")
    source = HuggingFaceDownloadSource("org/model", filesystem=filesystem)

    stream = source.open("model.bin")

    assert stream.read() == b"model bytes"
    assert filesystem.calls == [("org/model/model.bin", "rb")]


def test_open_includes_revision_in_repo_path() -> None:
    filesystem = FakeFilesystem()
    source = HuggingFaceDownloadSource("org/model", revision="main", filesystem=filesystem)

    source.open("model.bin")

    assert filesystem.calls == [("org/model@main/model.bin", "rb")]


def test_nested_path_is_allowed() -> None:
    filesystem = FakeFilesystem()
    source = HuggingFaceDownloadSource("org/model", filesystem=filesystem)

    source.open("nested/model.bin")

    assert filesystem.calls == [("org/model/nested/model.bin", "rb")]


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.bin",
        "/tmp/outside.bin",
        "nested\\..\\outside.bin",
        "C:\\tmp\\outside.bin",
    ],
)
def test_unsafe_paths_are_rejected_without_filesystem_call(unsafe_path: str) -> None:
    filesystem = FakeFilesystem()
    source = HuggingFaceDownloadSource("org/model", filesystem=filesystem)

    with pytest.raises(ValueError, match="remote path is unsafe"):
        source.open(unsafe_path)

    assert filesystem.calls == []


def test_filesystem_error_is_wrapped_with_generic_message(tmp_path: Path) -> None:
    filesystem = FakeFilesystem(
        error=RuntimeError(
            f"token-secret from https://huggingface.co/org/model at {tmp_path}"
        )
    )
    source = HuggingFaceDownloadSource(
        "org/model",
        token="token-secret",
        filesystem=filesystem,
    )

    with pytest.raises(HuggingFaceDownloadSourceError) as error:
        source.open("model.bin")

    message = str(error.value)
    assert message == "failed to open Hugging Face file"
    assert "token-secret" not in message
    assert "https://huggingface.co" not in message
    assert str(tmp_path) not in message


def test_injected_filesystem_does_not_import_huggingface_hub(monkeypatch) -> None:
    filesystem = FakeFilesystem()
    source = HuggingFaceDownloadSource("org/model", filesystem=filesystem)
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "huggingface_hub":
            raise AssertionError("huggingface_hub must not be imported")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    source.open("model.bin")

    assert filesystem.calls == [("org/model/model.bin", "rb")]


def test_source_only_calls_binary_open_on_filesystem() -> None:
    filesystem = FakeFilesystem()
    source = HuggingFaceDownloadSource("org/model", filesystem=filesystem)

    source.open("model.bin")

    assert filesystem.calls == [("org/model/model.bin", "rb")]


def test_source_does_not_write_local_files(tmp_path: Path, monkeypatch) -> None:
    filesystem = FakeFilesystem()
    source = HuggingFaceDownloadSource("org/model", filesystem=filesystem)

    def fail_write_bytes(self, data):
        raise AssertionError("local file writes must not happen")

    def fail_mkdir(self, mode=0o777, parents=False, exist_ok=False):
        raise AssertionError("local directories must not be created")

    monkeypatch.setattr(Path, "write_bytes", fail_write_bytes)
    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    stream = source.open("model.bin")

    assert stream.read() == b"content"
    assert not (tmp_path / "model.bin").exists()
