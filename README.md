# Chakra Vault

Never redownload a 600GB model because your cache broke.

Chakra Vault is a public-safe toolkit for verifying and safely restoring local
LLM model files. The current implementation focuses on local verification,
provider-neutral planning, safe writes, and a thin Hugging Face model download
workflow exposed through a CLI.

## Current Status

Chakra Vault currently includes:

- public-safe package foundation and safety checks
- local SHA-256 verification primitives
- provider-neutral download planning
- safe download executor with `.part` files, verification, and atomic promotion
- read-only Hugging Face metadata and file-source bridge
- composed model download workflow
- thin `chakra-vault model download` CLI entrypoint

It does not yet include:

- API server
- TUI or web dashboard
- SQLite ledger
- background job scheduler
- restore-test automation
- monitoring daemon
- Hugging Face upload, push, publish, create-repo, or remote-delete flows
- bundled model weights or private inventories

## Quick Start

Install the package for local development:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run the test suite and safety checks:

```bash
python3 -m pytest
.venv/bin/python -m ruff check scripts tests src
python3 scripts/check_no_large_files.py .
python3 scripts/check_no_hf_upload.py .
python3 scripts/check_no_private_paths.py .
```

Run the model download CLI:

```bash
chakra-vault model download \
  --repo-id Qwen/Qwen2.5-0.5B-Instruct \
  --target-dir /tmp/chakra-vault-model \
  --revision main
```

See [CLI documentation](docs/cli.md) for arguments, summary fields, exit codes,
and privacy behavior. See [download workflow documentation](docs/download-workflow.md)
for the component boundaries behind the command.

## Documentation

- [Install](docs/install.md)
- [CLI](docs/cli.md)
- [Download workflow](docs/download-workflow.md)
- [Roadmap](docs/roadmap.md)
- [Release checklist](docs/release-checklist.md)
- [Changelog](CHANGELOG.md)

## Safety Rules

- No Hugging Face upload, push, publish, create-repo, or remote-delete flows.
- No model weights, local logs, database files, tokens, or personal paths in Git.
- No generated model inventories or private machine paths.
- Unit tests use temporary directories and fake sources instead of real model
  downloads.
