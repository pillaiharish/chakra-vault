# Testing

Phase 0 tests cover package import and the public-safety scripts. They use
temporary files only and do not download models or require network access.

Install development dependencies in a local environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run the Phase 0 checks:

```bash
python3 -m pytest tests/test_import.py tests/test_safety_scripts.py
python3 -m ruff check scripts tests/test_import.py tests/test_safety_scripts.py src/chakra_vault/__init__.py
python3 scripts/check_no_large_files.py .
python3 scripts/check_no_hf_upload.py .
python3 scripts/check_no_private_paths.py .
```

Full-repository tests, coverage gates, type checks, API tests, TUI tests, and
dashboard tests belong to future implementation phases, not PR 1.
