#!/usr/bin/env python3
"""Fail if text files contain local/private machine paths."""

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


def private_path_patterns() -> list[tuple[str, re.Pattern[str]]]:
    slash = "/"
    backslash = "\\"
    users = "Users"
    home = "home"
    return [
        (
            "macOS user path",
            re.compile(re.escape(slash + users + slash) + r"[A-Za-z0-9._-]+"),
        ),
        (
            "Linux user path",
            re.compile(re.escape(slash + home + slash) + r"[A-Za-z0-9._-]+"),
        ),
        (
            "Windows user path",
            re.compile(
                r"\b[A-Za-z]:" + re.escape(backslash + users + backslash) + r"[A-Za-z0-9._-]+",
                re.IGNORECASE,
            ),
        ),
        (
            "file URL user path",
            re.compile(r"file://" + re.escape(slash + users + slash) + r"[A-Za-z0-9._-]+"),
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


def find_private_paths(root: Path) -> list[tuple[Path, int, str]]:
    findings: list[tuple[Path, int, str]] = []
    patterns = private_path_patterns()
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
    findings = find_private_paths(root)
    if not findings:
        return 0

    print("Found local/private paths:", file=sys.stderr)
    for path, line_number, label in findings:
        print(f"- {relative(path, root)}:{line_number}: {label}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
