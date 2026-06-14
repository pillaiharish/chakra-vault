# Chakra Vault

Never redownload a 600GB model because your cache broke.

Chakra Vault verifies, cold-stores, restore-tests, and monitors your local LLM
collection. It is designed around one rule: the workflow engine may execute, but
the verifier decides truth and the database records evidence.

## Scope

Chakra Vault is a public-safe toolkit for:

- read-only Hugging Face model metadata resolution
- local file hash verification against pinned revisions
- upstream drift detection
- cold-storage copy planning and restore testing
- SQLite-backed job and event evidence
- API, CLI, TUI, and dashboard views over verified state

## Safety Rules

- No Hugging Face upload, push, publish, create-repo, or remote-delete flows.
- No model weights, local logs, database files, tokens, or personal paths in Git.
- No dashboard or TUI success state unless the database/verifier has evidence.
- Default tests use fixtures and temporary directories, not large model downloads.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
chakra-vault health
pytest -q
```

## Developer Gates

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=chakra_vault --cov-fail-under=85
python scripts/check_no_large_files.py
python scripts/check_no_hf_upload.py
python scripts/check_no_private_paths.py
```
