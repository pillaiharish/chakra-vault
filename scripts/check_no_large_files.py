#!/usr/bin/env python3
"""Fail if repository files exceed the configured size limit."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

DEFAULT_MAX_BYTES = 10 * 1024 * 1024
SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "site",
}


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and not path.is_symlink():
            yield path


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def find_large_files(root: Path, max_bytes: int) -> list[tuple[Path, int]]:
    findings: list[tuple[Path, int]] = []
    for path in iter_files(root):
        size = path.stat().st_size
        if size > max_bytes:
            findings.append((path, size))
    return findings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--max-bytes", default=DEFAULT_MAX_BYTES, type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = args.root.resolve()
    findings = find_large_files(root, args.max_bytes)
    if not findings:
        return 0

    print(f"Found files larger than {args.max_bytes} bytes:", file=sys.stderr)
    for path, size in findings:
        print(f"- {relative(path, root)} ({size} bytes)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
