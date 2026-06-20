from __future__ import annotations

from chakra_vault.cli import main


def test_root_help(capsys) -> None:
    assert main(["--help"]) == 0

    output = capsys.readouterr().out
    assert "chakra-vault" in output
    assert "model" in output


def test_root_no_args_shows_help(capsys) -> None:
    assert main([]) == 0

    captured = capsys.readouterr()
    assert "chakra-vault" in captured.out
    assert "model" in captured.out
    assert captured.err == ""


def test_model_help(capsys) -> None:
    assert main(["model", "--help"]) == 0

    output = capsys.readouterr().out
    assert "download" in output


def test_model_no_args_shows_help(capsys) -> None:
    assert main(["model"]) == 0

    captured = capsys.readouterr()
    assert "download" in captured.out
    assert captured.err == ""


def test_model_download_help(capsys) -> None:
    assert main(["model", "download", "--help"]) == 0

    output = capsys.readouterr().out
    assert "--repo-id" in output
    assert "--target-dir" in output
    assert "--revision" in output
    assert "--dry-run" in output


def test_model_download_missing_target_dir(capsys) -> None:
    assert main(["model", "download", "--repo-id", "org/model"]) != 0

    error = capsys.readouterr().err
    assert "--target-dir" in error
