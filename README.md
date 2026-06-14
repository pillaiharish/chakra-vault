# Chakra Vault

Never redownload a 600GB model because your cache broke.

Chakra Vault will verify, cold-store, restore-test, and monitor local LLM
collections. This first PR is only the public-safe foundation for that work.

## Phase 0 Scope

This repository starts with:

- Python package metadata and import smoke test
- public-safe project documentation
- safety scripts for large files, Hub upload behavior, and private paths
- CI that runs the Phase 0 tests and safety checks

This PR does not include the download engine, API, CLI, TUI, web dashboard,
SQLite ledger, examples, model inventories, or copied legacy Chakra
implementation.

## Safety Rules

- No Hugging Face upload, push, publish, create-repo, or remote-delete flows.
- No model weights, local logs, database files, tokens, or personal paths in Git.
- No old workspace content, generated inventories, or private machine paths.
- Default tests use temporary directories, not model downloads.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest tests/test_import.py tests/test_safety_scripts.py
```

## Phase 0 Checks

```bash
python3 -m pytest tests/test_import.py tests/test_safety_scripts.py
python3 -m ruff check scripts tests/test_import.py tests/test_safety_scripts.py src/chakra_vault/__init__.py
python3 scripts/check_no_large_files.py .
python3 scripts/check_no_hf_upload.py .
python3 scripts/check_no_private_paths.py .
```
