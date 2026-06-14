# Architecture

Chakra Vault is an evidence-first local LLM vault. It separates planning,
execution, verification, and explanation so user-facing interfaces never invent
completion.

## Sources Of Truth

- SQLite stores models, revisions, files, jobs, events, provider calls, guardrail
  findings, and disaster-recovery scores.
- The verifier determines local integrity against a pinned remote revision.
- Drift checks compare the pinned revision with the latest remote revision.
- API, CLI, TUI, and web surfaces read database state and receipts.

## Main Subsystems

- `core`: typed states, events, configuration, and shared exceptions.
- `db`: SQLite engine, SQLAlchemy models, and repository helpers.
- `hf`: read-only Hugging Face metadata resolution and no-upload policy.
- `verify`: local hashing, source verification, drift checks, and receipts.
- `storage`: storage profiles, copy planning, restore testing, and safe delete.
- `jobs`: in-process job orchestration, progress, and retry state.
- `api`, `cli`, `tui`: interfaces over database-backed evidence.

## Golden Rule

The LLM can plan. The workflow engine can execute. The verifier decides truth.
The database records evidence. The TUI and dashboard explain it.
# Architecture

Chakra Vault is a public-safe, read-only-first tool for inventorying and
protecting local LLM artifacts. Phase 0 establishes the project skeleton,
documentation, CI, and repository safety checks. It does not include model
download, upload, restore, or migration behavior.

## Components

- `src/chakra_vault/`: importable Python package placeholder.
- `scripts/check_no_large_files.py`: rejects oversized files before they enter
  the repository.
- `scripts/check_no_hf_upload.py`: rejects Hugging Face Hub upload APIs and CLI
  upload commands.
- `scripts/check_no_private_paths.py`: rejects local machine paths that can leak
  user names or workspace layout.
- `.github/workflows/ci.yml`: runs lint, tests, and safety checks for pull
  requests and pushes.

## Phase 0 Boundaries

The repository must remain safe to publish. Source files may describe vault
behavior, but must not include private logs, local absolute paths, API tokens,
downloaded model files, generated inventories from a private machine, or any
script that uploads artifacts to a model hub.

Future phases can add inventory and restore workflows, but they should preserve
the Phase 0 safety gates as required CI checks.
