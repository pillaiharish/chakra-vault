from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

import chakra_vault.cli as cli
from chakra_vault.verify import VerificationStatus


def _workflow_result(
    *,
    repo_id: str = "org/model",
    revision: str | None = None,
    failed_count: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        repo_id=repo_id,
        revision=revision,
        plan=SimpleNamespace(download_count=1, redownload_count=0),
        execution=SimpleNamespace(
            downloaded_count=1,
            redownloaded_count=0,
            skipped_count=0,
            failed_count=failed_count,
        ),
        verification=SimpleNamespace(status=VerificationStatus.MATCH_PINNED),
    )


def _plan_result(
    *,
    repo_id: str = "org/model",
    revision: str | None = None,
    planned_download_bytes: int | None = 123,
) -> SimpleNamespace:
    return SimpleNamespace(
        repo_id=repo_id,
        revision=revision,
        plan=SimpleNamespace(
            download_count=2,
            redownload_count=1,
            skip_count=3,
            unverified_count=4,
            extra_count=5,
            metadata_missing_count=6,
            planned_download_bytes=planned_download_bytes,
        ),
    )


def test_cli_help_exits_successfully(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "chakra-vault" in captured.out
    assert "model" in captured.out


def test_cli_no_args_prints_root_help_without_error(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "chakra-vault" in captured.out
    assert "model" in captured.out
    assert captured.err == ""


def test_model_no_args_prints_model_help_without_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["model"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "download" in captured.out
    assert captured.err == ""


def test_missing_required_args_exit_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["model", "download", "--repo-id", "org/model"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "--target-dir" in captured.err


def test_model_download_calls_workflow_with_expected_arguments(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, object, str | None]] = []

    def fake_download(repo_id, root, *, revision=None):
        calls.append((repo_id, root, revision))
        return _workflow_result(repo_id=repo_id, revision=revision)

    monkeypatch.setattr(cli, "download_huggingface_model", fake_download)

    exit_code = cli.main(
        [
            "model",
            "download",
            "--repo-id",
            "org/model",
            "--target-dir",
            str(tmp_path),
            "--revision",
            "main",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls == [("org/model", tmp_path, "main")]
    assert "repo_id: org/model" in captured.out
    assert "verification: MATCH_PINNED" in captured.out


def test_workflow_failure_prints_generic_error_and_exits_nonzero(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_download(repo_id, root, *, revision=None):
        raise RuntimeError(f"token-secret at https://huggingface.co from {tmp_path}")

    monkeypatch.setattr(cli, "download_huggingface_model", fail_download)

    exit_code = cli.main(
        [
            "model",
            "download",
            "--repo-id",
            "org/model",
            "--target-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err.strip() == "error: model download failed"
    assert "token-secret" not in captured.err
    assert "https://huggingface.co" not in captured.err
    assert str(tmp_path) not in captured.err


def test_execution_failures_return_nonzero_without_raw_errors(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_download(repo_id, root, *, revision=None):
        return _workflow_result(repo_id=repo_id, revision=revision, failed_count=1)

    monkeypatch.setattr(cli, "download_huggingface_model", fake_download)

    exit_code = cli.main(
        [
            "model",
            "download",
            "--repo-id",
            "org/model",
            "--target-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "failed: 1" in captured.out
    assert captured.err == ""


def test_dry_run_calls_plan_workflow_and_not_download_workflow(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan_calls: list[tuple[str, object, str | None]] = []
    download_calls: list[tuple[str, object, str | None]] = []

    def fake_plan(repo_id, root, *, revision=None):
        plan_calls.append((repo_id, root, revision))
        return _plan_result(repo_id=repo_id, revision=revision)

    def fake_download(repo_id, root, *, revision=None):
        download_calls.append((repo_id, root, revision))
        raise AssertionError("download workflow must not be called")

    monkeypatch.setattr(cli, "plan_huggingface_model_download", fake_plan)
    monkeypatch.setattr(cli, "download_huggingface_model", fake_download)

    exit_code = cli.main(
        [
            "model",
            "download",
            "--repo-id",
            "org/model",
            "--target-dir",
            str(tmp_path),
            "--revision",
            "main",
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert plan_calls == [("org/model", tmp_path, "main")]
    assert download_calls == []
    assert "repo_id: org/model" in captured.out
    assert "revision: main" in captured.out
    assert "dry_run: true" in captured.out
    assert "planned_downloads: 2" in captured.out
    assert "planned_redownloads: 1" in captured.out
    assert "skipped: 3" in captured.out
    assert "unverified: 4" in captured.out
    assert "extra: 5" in captured.out
    assert "remote_metadata_missing: 6" in captured.out
    assert "planned_download_bytes: 123" in captured.out


def test_dry_run_unknown_planned_download_bytes_prints_unknown(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_plan(repo_id, root, *, revision=None):
        return _plan_result(repo_id=repo_id, revision=revision, planned_download_bytes=None)

    monkeypatch.setattr(cli, "plan_huggingface_model_download", fake_plan)

    exit_code = cli.main(
        [
            "model",
            "download",
            "--repo-id",
            "org/model",
            "--target-dir",
            str(tmp_path),
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "planned_download_bytes: unknown" in captured.out


def test_dry_run_failure_prints_generic_error_and_exits_nonzero(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_plan(repo_id, root, *, revision=None):
        raise RuntimeError(f"token-secret at https://huggingface.co from {tmp_path}")

    monkeypatch.setattr(cli, "plan_huggingface_model_download", fail_plan)

    exit_code = cli.main(
        [
            "model",
            "download",
            "--repo-id",
            "org/model",
            "--target-dir",
            str(tmp_path),
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err.strip() == "error: model download planning failed"
    assert "token-secret" not in captured.err
    assert "https://huggingface.co" not in captured.err
    assert str(tmp_path) not in captured.err


def test_cli_module_does_not_import_forbidden_helpers() -> None:
    source = inspect.getsource(cli)

    assert "hf_hub_download" not in source
    assert "snapshot_download" not in source
    assert "upload" not in source
    assert "push" not in source
    assert "create_repo" not in source
    assert "delete_repo" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "urllib" not in source
    assert "sqlite" not in source
