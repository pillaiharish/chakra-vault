"""Command-line entrypoint for Chakra Vault."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from chakra_vault.workflows import (
    download_huggingface_model,
    plan_huggingface_model_download,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Chakra Vault command-line interface."""

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return _exit_code(error)

    if args.command == "model" and args.model_command == "download":
        return _run_model_download(args)

    parser.print_help(sys.stderr)
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chakra-vault")
    subparsers = parser.add_subparsers(dest="command", required=True)

    model_parser = subparsers.add_parser("model")
    model_subparsers = model_parser.add_subparsers(dest="model_command", required=True)

    download_parser = model_subparsers.add_parser("download")
    download_parser.add_argument("--repo-id", required=True)
    download_parser.add_argument("--target-dir", required=True)
    download_parser.add_argument("--revision")
    download_parser.add_argument("--dry-run", action="store_true")
    return parser


def _run_model_download(args: argparse.Namespace) -> int:
    if args.dry_run:
        return _run_model_download_dry_run(args)

    try:
        result = download_huggingface_model(
            args.repo_id,
            Path(args.target_dir),
            revision=args.revision,
        )
    except Exception:
        print("error: model download failed", file=sys.stderr)
        return 1

    print(f"repo_id: {result.repo_id}")
    print(f"revision: {result.revision or 'default'}")
    print(f"planned_downloads: {result.plan.download_count}")
    print(f"planned_redownloads: {result.plan.redownload_count}")
    print(f"downloaded: {result.execution.downloaded_count}")
    print(f"redownloaded: {result.execution.redownloaded_count}")
    print(f"skipped: {result.execution.skipped_count}")
    print(f"failed: {result.execution.failed_count}")
    print(f"verification: {result.verification.status}")
    return 0 if result.execution.failed_count == 0 else 1


def _run_model_download_dry_run(args: argparse.Namespace) -> int:
    try:
        result = plan_huggingface_model_download(
            args.repo_id,
            Path(args.target_dir),
            revision=args.revision,
        )
    except Exception:
        print("error: model download planning failed", file=sys.stderr)
        return 1

    print(f"repo_id: {result.repo_id}")
    print(f"revision: {result.revision or 'default'}")
    print("dry_run: true")
    print(f"planned_downloads: {result.plan.download_count}")
    print(f"planned_redownloads: {result.plan.redownload_count}")
    print(f"skipped: {result.plan.skip_count}")
    print(f"unverified: {result.plan.unverified_count}")
    print(f"extra: {result.plan.extra_count}")
    print(f"remote_metadata_missing: {result.plan.metadata_missing_count}")
    print(f"planned_download_bytes: {_format_optional_bytes(result.plan.planned_download_bytes)}")
    return 0


def _format_optional_bytes(value: int | None) -> str:
    if value is None:
        return "unknown"
    return str(value)


def _exit_code(error: SystemExit) -> int:
    if isinstance(error.code, int):
        return error.code
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
