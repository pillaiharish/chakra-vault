from __future__ import annotations

import builtins
import hashlib
from io import BytesIO
from pathlib import Path

import pytest

from chakra_vault.downloader import DownloadExecutionStatus, execute_download_plan
from chakra_vault.planner import DownloadPlan, DownloadPlanAction, DownloadPlanItem


class FakeDownloadSource:
    def __init__(self, files: dict[str, bytes] | None = None, fail_paths: set[str] | None = None):
        self.files = files or {}
        self.fail_paths = fail_paths or set()
        self.calls: list[str] = []

    def open(self, path: str):
        self.calls.append(path)
        if path in self.fail_paths:
            return FailingStream(self.files.get(path, b""))
        return BytesIO(self.files[path])


class FailingStream(BytesIO):
    def read(self, size: int = -1) -> bytes:
        chunk = super().read(size)
        if chunk:
            return chunk
        raise OSError("source failed with private details")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _item(
    path: str,
    action: DownloadPlanAction,
    *,
    expected_size_bytes: int | None = None,
    expected_sha256: str | None = None,
) -> DownloadPlanItem:
    return DownloadPlanItem(
        path=path,
        action=action,
        reason="test plan item",
        expected_size_bytes=expected_size_bytes,
        actual_size_bytes=None,
        expected_sha256=expected_sha256,
        actual_sha256=None,
        etag=None,
        is_lfs=True,
    )


def _plan(*items: DownloadPlanItem) -> DownloadPlan:
    return DownloadPlan(
        items=items,
        download_count=sum(
            1 for item in items if item.action is DownloadPlanAction.DOWNLOAD_MISSING
        ),
        redownload_count=sum(
            1 for item in items if item.action is DownloadPlanAction.REDOWNLOAD_CORRUPT
        ),
        skip_count=sum(1 for item in items if item.action is DownloadPlanAction.SKIP_VERIFIED),
        unverified_count=sum(
            1 for item in items if item.action is DownloadPlanAction.KEEP_UNVERIFIED
        ),
        extra_count=sum(
            1 for item in items if item.action is DownloadPlanAction.REPORT_EXTRA_LOCAL
        ),
        metadata_missing_count=sum(
            1 for item in items if item.action is DownloadPlanAction.REPORT_REMOTE_METADATA_MISSING
        ),
        planned_download_bytes=None,
    )


def test_download_missing_writes_file_through_fake_source(tmp_path: Path) -> None:
    content = b"new file"
    source = FakeDownloadSource({"model.bin": content})

    summary = execute_download_plan(
        tmp_path,
        _plan(
            _item(
                "model.bin",
                DownloadPlanAction.DOWNLOAD_MISSING,
                expected_size_bytes=len(content),
                expected_sha256=_sha256(content),
            )
        ),
        source,
        chunk_size=3,
    )

    assert (tmp_path / "model.bin").read_bytes() == content
    assert source.calls == ["model.bin"]
    assert summary.results[0].status is DownloadExecutionStatus.DOWNLOADED
    assert summary.downloaded_count == 1
    assert summary.bytes_written == len(content)


def test_redownload_corrupt_replaces_old_file_after_success(tmp_path: Path) -> None:
    old_content = b"old"
    new_content = b"new verified"
    path = tmp_path / "model.bin"
    path.write_bytes(old_content)
    source = FakeDownloadSource({"model.bin": new_content})

    summary = execute_download_plan(
        tmp_path,
        _plan(
            _item(
                "model.bin",
                DownloadPlanAction.REDOWNLOAD_CORRUPT,
                expected_size_bytes=len(new_content),
                expected_sha256=_sha256(new_content),
            )
        ),
        source,
    )

    assert path.read_bytes() == new_content
    assert summary.results[0].status is DownloadExecutionStatus.REDOWNLOADED
    assert summary.redownloaded_count == 1
    assert summary.bytes_written == len(new_content)


@pytest.mark.parametrize(
    "action",
    [
        DownloadPlanAction.SKIP_VERIFIED,
        DownloadPlanAction.KEEP_UNVERIFIED,
        DownloadPlanAction.REPORT_EXTRA_LOCAL,
        DownloadPlanAction.REPORT_REMOTE_METADATA_MISSING,
    ],
)
def test_non_download_actions_are_skipped_and_source_is_not_called(
    tmp_path: Path, action: DownloadPlanAction
) -> None:
    source = FakeDownloadSource({"model.bin": b"content"})

    summary = execute_download_plan(tmp_path, _plan(_item("model.bin", action)), source)

    assert summary.results[0].status is DownloadExecutionStatus.SKIPPED
    assert summary.skipped_count == 1
    assert source.calls == []


def test_expected_sha_mismatch_fails_and_leaves_no_final_content(tmp_path: Path) -> None:
    source = FakeDownloadSource({"model.bin": b"wrong"})

    summary = execute_download_plan(
        tmp_path,
        _plan(
            _item(
                "model.bin",
                DownloadPlanAction.DOWNLOAD_MISSING,
                expected_size_bytes=5,
                expected_sha256=_sha256(b"right"),
            )
        ),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.FAILED
    assert not (tmp_path / "model.bin").exists()
    assert not (tmp_path / "model.bin.part").exists()


def test_expected_size_mismatch_fails(tmp_path: Path) -> None:
    source = FakeDownloadSource({"model.bin": b"too small"})

    summary = execute_download_plan(
        tmp_path,
        _plan(
            _item(
                "model.bin",
                DownloadPlanAction.DOWNLOAD_MISSING,
                expected_size_bytes=100,
                expected_sha256=None,
            )
        ),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.FAILED
    assert not (tmp_path / "model.bin").exists()
    assert not (tmp_path / "model.bin.part").exists()


def test_source_failure_cleans_part_and_uses_generic_message(tmp_path: Path) -> None:
    source = FakeDownloadSource({"model.bin": b"partial"}, fail_paths={"model.bin"})

    summary = execute_download_plan(
        tmp_path,
        _plan(_item("model.bin", DownloadPlanAction.DOWNLOAD_MISSING)),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.FAILED
    assert summary.results[0].message == "download execution failed"
    assert str(tmp_path) not in summary.results[0].message
    assert not (tmp_path / "model.bin.part").exists()


def test_redownload_source_failure_preserves_old_final_file(tmp_path: Path) -> None:
    old_content = b"old content"
    (tmp_path / "model.bin").write_bytes(old_content)
    source = FakeDownloadSource({"model.bin": b"partial"}, fail_paths={"model.bin"})

    summary = execute_download_plan(
        tmp_path,
        _plan(_item("model.bin", DownloadPlanAction.REDOWNLOAD_CORRUPT)),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.FAILED
    assert (tmp_path / "model.bin").read_bytes() == old_content
    assert not (tmp_path / "model.bin.part").exists()


@pytest.mark.parametrize("unsafe_path", ["../outside.bin", "/tmp/outside.bin"])
def test_unsafe_plan_paths_fail_without_local_paths(tmp_path: Path, unsafe_path: str) -> None:
    source = FakeDownloadSource({unsafe_path: b"content"})

    summary = execute_download_plan(
        tmp_path,
        _plan(_item(unsafe_path, DownloadPlanAction.DOWNLOAD_MISSING)),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.FAILED
    assert summary.results[0].message == "plan item path is unsafe"
    assert str(tmp_path) not in summary.results[0].message
    assert source.calls == []


def test_final_path_symlink_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.bin"
    target.write_bytes(b"target")
    link = tmp_path / "model.bin"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("current platform cannot create symlinks")
    source = FakeDownloadSource({"model.bin": b"content"})

    summary = execute_download_plan(
        tmp_path,
        _plan(_item("model.bin", DownloadPlanAction.REDOWNLOAD_CORRUPT)),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.FAILED
    assert link.is_symlink()


def test_parent_directory_symlink_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "nested"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("current platform cannot create symlinks")
    source = FakeDownloadSource({"nested/model.bin": b"content"})

    summary = execute_download_plan(
        tmp_path,
        _plan(_item("nested/model.bin", DownloadPlanAction.DOWNLOAD_MISSING)),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.FAILED
    assert not (outside / "model.bin").exists()


def test_root_symlink_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    link = tmp_path / "root-link"
    try:
        link.symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip("current platform cannot create symlinks")
    source = FakeDownloadSource({"model.bin": b"content"})

    summary = execute_download_plan(
        link,
        _plan(_item("model.bin", DownloadPlanAction.DOWNLOAD_MISSING)),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.FAILED
    assert not (root / "model.bin").exists()


def test_nested_path_works(tmp_path: Path) -> None:
    content = b"nested content"
    source = FakeDownloadSource({"nested/model.bin": content})

    summary = execute_download_plan(
        tmp_path,
        _plan(
            _item(
                "nested/model.bin",
                DownloadPlanAction.DOWNLOAD_MISSING,
                expected_size_bytes=len(content),
                expected_sha256=_sha256(content),
            )
        ),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.DOWNLOADED
    assert (tmp_path / "nested" / "model.bin").read_bytes() == content


def test_result_counts_and_bytes_written_are_correct(tmp_path: Path) -> None:
    first = b"first"
    second = b"second"
    (tmp_path / "second.bin").write_bytes(b"old")
    source = FakeDownloadSource({"first.bin": first, "second.bin": second})

    summary = execute_download_plan(
        tmp_path,
        _plan(
            _item(
                "first.bin",
                DownloadPlanAction.DOWNLOAD_MISSING,
                expected_size_bytes=len(first),
                expected_sha256=_sha256(first),
            ),
            _item(
                "second.bin",
                DownloadPlanAction.REDOWNLOAD_CORRUPT,
                expected_size_bytes=len(second),
                expected_sha256=_sha256(second),
            ),
            _item("skip.bin", DownloadPlanAction.SKIP_VERIFIED),
            _item("bad.bin", DownloadPlanAction.DOWNLOAD_MISSING, expected_size_bytes=99),
        ),
        source,
    )

    assert [result.status for result in summary.results] == [
        DownloadExecutionStatus.DOWNLOADED,
        DownloadExecutionStatus.REDOWNLOADED,
        DownloadExecutionStatus.SKIPPED,
        DownloadExecutionStatus.FAILED,
    ]
    assert summary.downloaded_count == 1
    assert summary.redownloaded_count == 1
    assert summary.skipped_count == 1
    assert summary.failed_count == 1
    assert summary.bytes_written == len(first) + len(second)


def test_executor_does_not_import_provider_modules(tmp_path: Path, monkeypatch) -> None:
    content = b"content"
    source = FakeDownloadSource({"model.bin": content})
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("chakra_vault.providers"):
            raise AssertionError("executor imported provider code")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    summary = execute_download_plan(
        tmp_path,
        _plan(
            _item(
                "model.bin",
                DownloadPlanAction.DOWNLOAD_MISSING,
                expected_size_bytes=len(content),
                expected_sha256=_sha256(content),
            )
        ),
        source,
    )

    assert summary.results[0].status is DownloadExecutionStatus.DOWNLOADED
