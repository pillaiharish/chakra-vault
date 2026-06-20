# Release Checklist

Use this checklist for the `v0.1.0` release candidate.

## Validation

Run:

```bash
python3 -m pytest
.venv/bin/python -m ruff check scripts tests src
python3 scripts/check_no_large_files.py .
python3 scripts/check_no_hf_upload.py .
python3 scripts/check_no_private_paths.py .
git diff --check
git status --short
```

## Review

- Verify README links.
- Verify `docs/cli.md` examples.
- Verify no local or private paths are present.
- Verify no model weights, inventories, logs, caches, or database files are
  staged.
- Verify no Hugging Face upload, push, publish, create-repo, or delete flows are
  present.
- Verify GitHub Actions passes on Python 3.11 and 3.12.

## Tag

Run these only after all checks pass and the release commit is on `main`:

```bash
git checkout main
git pull --ff-only
git tag -a v0.1.0 -m "Chakra Vault v0.1.0"
git push origin v0.1.0
```

## GitHub Release

Create GitHub release notes from `CHANGELOG.md` and the merged pull requests for
the release.
