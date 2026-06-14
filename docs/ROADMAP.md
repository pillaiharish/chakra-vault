# Roadmap

## Phase 0

Public-safe repo foundation, safety scripts, CI, docs, package skeleton.

## Phase 1

SQLite ledger, append-only events, and strict state machine.

## Phase 2

Read-only Hugging Face resolver and no-upload policy.

## Phase 3

Local hashing, verification, drift detection, and receipts.

## Phase 4

Storage planning, job runner, API, TUI, and read-only dashboard.
# Roadmap

## Phase 0: Foundation

- Python package skeleton.
- Public-safe repository defaults.
- CI for lint, tests, import checks, and safety scripts.
- Documentation for architecture, testing, security, and Hub upload policy.

## Phase 1: Read-Only Inventory

- Discover local model artifact directories from user-provided roots.
- Compute size, file count, and checksum metadata.
- Write sanitized manifests with relative paths only.
- Keep network behavior disabled by default.

## Phase 2: Cold Storage Planning

- Plan copy and verification jobs without executing destructive actions.
- Estimate storage requirements.
- Validate restore plans against checksums.

## Phase 3: Restore Testing

- Restore small sample artifacts into temporary locations.
- Verify checksums and manifest consistency.
- Report missing, corrupt, or unexpected files.

## Phase 4: Monitoring

- Track local inventory drift.
- Alert on missing or changed artifacts.
- Keep private paths and logs out of generated reports.
