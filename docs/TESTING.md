# Testing

Tests use small fixtures and temporary directories. Default tests must not
download real models or require network access.

## Required Gates

```bash
ruff check .
ruff format --check .
mypy src
pytest tests/unit -q
pytest tests/integration -q
pytest --cov=chakra_vault --cov-fail-under=85
python scripts/check_no_large_files.py
python scripts/check_no_hf_upload.py
python scripts/check_no_private_paths.py
```

## Coverage Targets

- state-machine transitions and illegal transition failures
- SQLite initialization and WAL mode
- append-only events
- read-only HF resolver behavior with fakes
- no-upload policy and static scanner
- local hash verification and drift receipts
- API responses sourced from DB state
- TUI command parsing and rendering snapshots
# Testing

Install development dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

Run the Phase 0 foundation tests:

```bash
python3 -m pytest tests/test_import.py tests/test_safety_scripts.py
```

Run lint for the Phase 0 foundation surface:

```bash
python3 -m ruff check scripts tests/test_import.py tests/test_safety_scripts.py src/chakra_vault/__init__.py
```

Run public-safety checks:

```bash
python3 scripts/check_no_large_files.py .
python3 scripts/check_no_hf_upload.py .
python3 scripts/check_no_private_paths.py .
```

The safety checks scan the repository tree while skipping Git metadata, virtual
environments, build outputs, and common cache directories. Tests for the checks
use temporary fixtures and should not require network access.
