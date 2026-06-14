# Security

Chakra Vault is designed to be public-safe and local-first.

## Repository Safety

- Do not commit model weights, local logs, database files, tokens, or personal
  filesystem paths.
- Use synthetic demo data only.
- Keep destructive operations behind explicit evidence gates.
- Run the safety scripts before merge.

## Runtime Safety

- Hugging Face operations are read-only and download-only.
- Safe delete requires source verification plus coldstore/restore evidence.
- UI success states must come from the database, not generated prose.
# Security

Chakra Vault handles metadata about local LLM artifacts. Treat that metadata as
sensitive because file names, paths, logs, and manifests can reveal private
machine details.

## Public-Safe Rules

- Do not commit model weights, datasets, logs, generated inventories, or caches.
- Do not commit absolute local paths.
- Do not commit secrets, tokens, cookies, service credentials, or private config.
- Do not add Hub upload behavior.
- Prefer relative paths in examples and generated output.

## Repository Checks

Run these before opening a pull request:

```bash
python3 scripts/check_no_large_files.py .
python3 scripts/check_no_hf_upload.py .
python3 scripts/check_no_private_paths.py .
python3 -m pytest
```

The CI workflow runs the same checks. If a check fails, remove the unsafe
content instead of adding an allowlist.

## Reporting Issues

Open a private maintainer discussion for security-sensitive reports. Do not
paste secrets, local manifests, logs, or machine-specific paths into public
issues.
