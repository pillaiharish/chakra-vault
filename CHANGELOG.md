# Changelog

## Unreleased

- Release readiness documentation for the `v0.1.0` candidate.

## v0.1.0 candidate

Chakra Vault currently includes:

- public-safe package foundation
- safety checks for large files, Hugging Face upload behavior, and private paths
- local SHA-256 verification primitives
- provider-neutral download planning
- safe download executor using `.part` files and atomic promotion
- read-only Hugging Face metadata and file-source bridge
- composed model download workflow
- `chakra-vault model download` CLI
- `--dry-run` plan-only CLI mode
- full CI on Python 3.11 and 3.12

Not yet included:

- API server
- TUI or web dashboard
- SQLite ledger
- background scheduler or daemon
- restore-test automation
- monitoring daemon
- systemd, launchd, or Windows service installation
- Hugging Face upload, push, publish, create-repo, or delete flows
- bundled model weights or private inventories
