# Security

Chakra Vault Phase 0 keeps the repository safe to publish. Do not commit model
weights, datasets, logs, database files, generated inventories, private
configuration, secrets, tokens, or local absolute paths.

## Public-Safe Rules

- Use relative paths in examples and documentation.
- Keep generated caches and local runtime state out of Git.
- Do not add Hugging Face upload, push, publish, create, or delete behavior.
- Remove unsafe content instead of adding broad allowlists.
- Treat old Chakra code as reference material, not source to bulk copy.

## Phase 0 Checks

Run these before merge:

```bash
python3 -m pytest tests/test_import.py tests/test_safety_scripts.py
python3 -m ruff check scripts tests/test_import.py tests/test_safety_scripts.py src/chakra_vault/__init__.py
python3 scripts/check_no_large_files.py .
python3 scripts/check_no_hf_upload.py .
python3 scripts/check_no_private_paths.py .
```

Security-sensitive reports should not include secrets, local manifests, logs, or
machine-specific paths in public issues.
