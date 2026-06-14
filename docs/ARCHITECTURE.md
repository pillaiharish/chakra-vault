# Architecture

Chakra Vault Phase 0 is a public-safe foundation for a future local LLM vault.
This PR intentionally contains only the repository skeleton, documentation,
safety checks, CI, pull request template, and importable package placeholder.

## Phase 0 Components

- `src/chakra_vault/__init__.py`: package placeholder and version metadata.
- `scripts/check_no_large_files.py`: rejects oversized files in the repository.
- `scripts/check_no_hf_upload.py`: rejects Hugging Face upload, push, publish,
  create, and delete behavior in source text.
- `scripts/check_no_private_paths.py`: rejects local absolute paths that can
  expose user or machine details.
- `.github/workflows/ci.yml`: runs the Phase 0 lint, import tests, and safety
  checks.
- `.github/pull_request_template.md`: keeps public-safety review visible.

## Boundaries

PR 1 does not include an API, CLI, TUI, dashboard, SQLite ledger, download
engine, old Chakra implementation, model files, private inventories, logs, or
local configuration.

Future phases may add inventory, read-only metadata resolution, verification,
storage planning, downloads, and user interfaces. Those features must preserve
the Phase 0 safety checks and no-upload policy.
