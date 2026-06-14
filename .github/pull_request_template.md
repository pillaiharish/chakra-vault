## Summary

- 

## Safety Checklist

- [ ] No model weights, datasets, caches, logs, or generated private inventories.
- [ ] No local absolute paths or private workspace details.
- [ ] No Hub upload behavior or credentials.
- [ ] `python3 -m pytest tests/test_import.py tests/test_safety_scripts.py`
- [ ] `python3 -m ruff check scripts tests/test_import.py tests/test_safety_scripts.py src/chakra_vault/__init__.py`
- [ ] `python3 scripts/check_no_large_files.py .`
- [ ] `python3 scripts/check_no_hf_upload.py .`
- [ ] `python3 scripts/check_no_private_paths.py .`
