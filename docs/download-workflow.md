# Download Workflow

The model download workflow composes already-reviewed components. It does not
implement new downloader logic or direct file writes.

```text
Hugging Face metadata client
  -> download source
  -> provider-neutral plan
  -> safe executor
  -> final verification
  -> CLI summary
```

## Responsibilities

- Hugging Face metadata client reads remote file metadata.
- Hugging Face download source opens remote files as binary streams.
- Provider-neutral planner decides whether files are verified, missing,
  corrupt, unverified, extra, or missing remote metadata.
- Safe executor performs local writes through sibling `.part` files, verifies
  size and SHA-256 when available, and atomically promotes successful files.
- Workflow service composes metadata, planning, execution, and final
  verification.
- CLI parses arguments and displays a concise result summary.

## Boundaries

Chakra Vault does not add Hugging Face upload, push, publish, create-repo,
remote-delete, API server, TUI/web dashboard, SQLite ledger, background job, or
monitoring behavior in this workflow.

Tests for the workflow and CLI use temporary directories, fake metadata clients,
and fake download sources. They do not require real model downloads.
