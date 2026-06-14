#!/usr/bin/env python3
"""Fail if source files include model-hub upload behavior."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

MAX_TEXT_BYTES = 1_000_000
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
TEXT_EXTENSIONS = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def upload_word() -> str:
    return "up" + "load"


def forbidden_patterns() -> list[tuple[str, re.Pattern[str]]]:
    upload = upload_word()
    return [
        (
            "Hub CLI publish command",
            re.compile(rf"\bhuggingface-cli\s+{upload}\b", re.IGNORECASE),
        ),
        (
            "Hub Python file publish API",
            re.compile(rf"\b{upload}_file\s*\(", re.IGNORECASE),
        ),
        (
            "Hub Python folder publish API",
            re.compile(rf"\b{upload}_folder\s*\(", re.IGNORECASE),
        ),
        (
            "Hub Python large-folder publish API",
            re.compile(rf"\b{upload}_large_folder\s*\(", re.IGNORECASE),
        ),
        (
            "Hub push helper",
            re.compile(r"\bpush" + r"_to_hub\s*\(", re.IGNORECASE),
        ),
    ]


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def read_text(path: Path) -> str | None:
    if path.stat().st_size > MAX_TEXT_BYTES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def find_forbidden_usage(root: Path) -> list[tuple[Path, int, str]]:
    findings: list[tuple[Path, int, str]] = []
    patterns = forbidden_patterns()
    for path in iter_files(root):
        text = read_text(path)
        if text is None:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in patterns:
                if pattern.search(line):
                    findings.append((path, line_number, label))
    return findings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = args.root.resolve()
    findings = find_forbidden_usage(root)
    if not findings:
        return 0

    print("Found prohibited Hub upload behavior:", file=sys.stderr)
    for path, line_number, label in findings:
        print(f"- {relative(path, root)}:{line_number}: {label}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
