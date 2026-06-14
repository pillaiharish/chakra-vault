from __future__ import annotations

import builtins
import hashlib
from pathlib import Path

import pytest

from chakra_vault.planner import DownloadPlanAction, build_download_plan
from chakra_vault.verify import RemoteFileMetadata


def _write(tmp_path: Path, relative_path: str, content: bytes) -> Path:
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
    etag: str | None = "etag",
) -> RemoteFileMetadata:
    return RemoteFileMetadata(
        path=path,
        size_bytes=len(content) if content is not None else size_bytes,
        etag=etag,
        lfs_sha256=_sha256(content) if content is not None else lfs_sha256,
        is_lfs=is_lfs,
    )


def test_matching_pinned_local_file_becomes_skip_verified(tmp_path: Path) -> None:
    content = b"verified"
    _write(tmp_path, "model.bin", content)

    plan = build_download_plan(tmp_path, [_remote("model.bin", content=content)])

    assert plan.items[0].action is DownloadPlanAction.SKIP_VERIFIED
    assert plan.items[0].etag == "etag"
    assert plan.items[0].is_lfs is True
    assert plan.download_count == 0
    assert plan.skip_count == 1
    assert plan.planned_download_bytes == 0


def test_missing_expected_file_becomes_download_missing(tmp_path: Path) -> None:
    plan = build_download_plan(
        tmp_path,
        [_remote("missing.bin", size_bytes=12, lfs_sha256=_sha256(b"missing"))],
    )

    assert plan.items[0].action is DownloadPlanAction.DOWNLOAD_MISSING
    assert plan.download_count == 1
    assert plan.planned_download_bytes == 12


def test_corrupt_local_file_becomes_redownload_corrupt(tmp_path: Path) -> None:
    _write(tmp_path, "model.bin", b"actual")

    plan = build_download_plan(
        tmp_path,
        [_remote("model.bin", size_bytes=6, lfs_sha256=_sha256(b"expect"))],
    )

    assert plan.items[0].action is DownloadPlanAction.REDOWNLOAD_CORRUPT
    assert plan.redownload_count == 1
    assert plan.planned_download_bytes == 6


def test_non_lfs_local_file_becomes_keep_unverified(tmp_path: Path) -> None:
    content = b"readme"
    _write(tmp_path, "README.md", content)

    plan = build_download_plan(
        tmp_path,
        [
            _remote(
                "README.md",
                size_bytes=len(content),
                lfs_sha256=None,
                is_lfs=False,
                etag="git-blob",
            )
        ],
    )

    assert plan.items[0].action is DownloadPlanAction.KEEP_UNVERIFIED
    assert plan.items[0].etag == "git-blob"
    assert plan.items[0].is_lfs is False
    assert plan.unverified_count == 1
    assert plan.planned_download_bytes == 0


def test_lfs_missing_sha_metadata_becomes_report_metadata_missing(tmp_path: Path) -> None:
    content = b"metadata missing"
    _write(tmp_path, "model.bin", content)

    plan = build_download_plan(
        tmp_path,
        [_remote("model.bin", size_bytes=len(content), lfs_sha256=None, is_lfs=True)],
    )

    assert plan.items[0].action is DownloadPlanAction.REPORT_REMOTE_METADATA_MISSING
    assert plan.metadata_missing_count == 1


def test_extra_local_file_becomes_report_extra_local(tmp_path: Path) -> None:
    content = b"expected"
    _write(tmp_path, "expected.bin", content)
    _write(tmp_path, "extra.bin", b"extra")

    plan = build_download_plan(tmp_path, [_remote("expected.bin", content=content)])

    assert plan.items[0].action is DownloadPlanAction.SKIP_VERIFIED
    assert plan.items[1].path == "extra.bin"
    assert plan.items[1].action is DownloadPlanAction.REPORT_EXTRA_LOCAL
    assert plan.items[1].etag is None
    assert plan.items[1].is_lfs is None
    assert plan.extra_count == 1


def test_mixed_plan_counts_and_order_are_correct(tmp_path: Path) -> None:
    matched = b"matched"
    corrupt = b"actual!"
    docs = b"docs"
    _write(tmp_path, "z-extra.bin", b"extra-z")
    _write(tmp_path, "a-extra.bin", b"extra-a")
    _write(tmp_path, "matched.bin", matched)
    _write(tmp_path, "corrupt.bin", corrupt)
    _write(tmp_path, "docs.md", docs)
    _write(tmp_path, "metadata.bin", b"metadata")

    plan = build_download_plan(
        tmp_path,
        [
            _remote("matched.bin", content=matched),
            _remote("missing.bin", size_bytes=10, lfs_sha256=_sha256(b"missing")),
            _remote("corrupt.bin", size_bytes=len(corrupt), lfs_sha256=_sha256(b"wrong")),
            _remote("docs.md", size_bytes=len(docs), lfs_sha256=None, is_lfs=False),
            _remote("metadata.bin", size_bytes=8, lfs_sha256=None, is_lfs=True),
        ],
    )

    assert [item.action for item in plan.items] == [
        DownloadPlanAction.SKIP_VERIFIED,
        DownloadPlanAction.DOWNLOAD_MISSING,
        DownloadPlanAction.REDOWNLOAD_CORRUPT,
        DownloadPlanAction.KEEP_UNVERIFIED,
        DownloadPlanAction.REPORT_REMOTE_METADATA_MISSING,
        DownloadPlanAction.REPORT_EXTRA_LOCAL,
        DownloadPlanAction.REPORT_EXTRA_LOCAL,
    ]
    assert [item.path for item in plan.items[-2:]] == ["a-extra.bin", "z-extra.bin"]
    assert plan.download_count == 1
    assert plan.redownload_count == 1
    assert plan.skip_count == 1
    assert plan.unverified_count == 1
    assert plan.metadata_missing_count == 1
    assert plan.extra_count == 2
    assert plan.planned_download_bytes == 10 + len(corrupt)


def test_planned_download_bytes_is_none_when_any_planned_size_is_unknown(
    tmp_path: Path,
) -> None:
    plan = build_download_plan(
        tmp_path,
        [_remote("missing.bin", size_bytes=None, lfs_sha256=_sha256(b"missing"))],
    )

    assert plan.items[0].action is DownloadPlanAction.DOWNLOAD_MISSING
    assert plan.planned_download_bytes is None


def test_nested_path_works(tmp_path: Path) -> None:
    content = b"nested"
    _write(tmp_path, "nested/tokenizer.json", content)

    plan = build_download_plan(
        tmp_path,
        [_remote("nested/tokenizer.json", content=content)],
    )

    assert plan.items[0].path == "nested/tokenizer.json"
    assert plan.items[0].action is DownloadPlanAction.SKIP_VERIFIED


@pytest.mark.parametrize("unsafe_path", ["../outside.bin", "/tmp/outside.bin"])
def test_unsafe_paths_are_rejected_without_local_paths(
    tmp_path: Path, unsafe_path: str
) -> None:
    with pytest.raises(ValueError, match="remote path is unsafe") as error:
        build_download_plan(
            tmp_path,
            [_remote(unsafe_path, size_bytes=1, lfs_sha256=_sha256(b"x"))],
        )

    assert str(tmp_path) not in str(error.value)


def test_duplicate_expected_paths_are_rejected_without_local_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate remote path") as error:
        build_download_plan(
            tmp_path,
            [
                _remote("model.bin", size_bytes=1, lfs_sha256=_sha256(b"a")),
                _remote("model.bin", size_bytes=1, lfs_sha256=_sha256(b"b")),
            ],
        )

    assert str(tmp_path) not in str(error.value)


def test_planner_does_not_import_provider_clients(tmp_path: Path, monkeypatch) -> None:
    content = b"verified"
    _write(tmp_path, "model.bin", content)
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("chakra_vault.providers"):
            raise AssertionError("planner imported provider code")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    plan = build_download_plan(tmp_path, [_remote("model.bin", content=content)])

    assert plan.items[0].action is DownloadPlanAction.SKIP_VERIFIED


def test_planner_does_not_write_files(tmp_path: Path, monkeypatch) -> None:
    content = b"verified"
    _write(tmp_path, "model.bin", content)

    def fail_write(*args, **kwargs):
        raise AssertionError("planner attempted to write a file")

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    monkeypatch.setattr(Path, "write_text", fail_write)

    plan = build_download_plan(tmp_path, [_remote("model.bin", content=content)])

    assert plan.items[0].action is DownloadPlanAction.SKIP_VERIFIED
