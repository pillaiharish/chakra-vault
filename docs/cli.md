# CLI

Chakra Vault exposes a thin command-line adapter for the existing model download
workflow.

```bash
chakra-vault model download \
  --repo-id Qwen/Qwen2.5-0.5B-Instruct \
  --target-dir /tmp/chakra-vault-model \
  --revision main
```

## Dry Run

Use `--dry-run` to inspect the provider-neutral download plan without writing
model files:

```bash
chakra-vault model download \
  --repo-id Qwen/Qwen2.5-0.5B-Instruct \
  --target-dir /tmp/chakra-vault-model \
  --revision main \
  --dry-run
```

Dry-run mode fetches read-only Hugging Face metadata and builds the download
plan. It does not construct the Hugging Face download source, call the safe
executor, create files, modify files, delete files, download model files, or
promote `.part` files.

## Arguments

- `--repo-id`: Hugging Face model repository identifier, such as
  `Qwen/Qwen2.5-0.5B-Instruct`.
- `--target-dir`: local directory where the workflow verifies existing files and
  where the safe executor promotes downloaded files.
- `--revision`: optional model revision, branch, tag, or commit.
- `--dry-run`: plan only; perform no downloads or writes.

## Help Behavior

These commands print help to stdout and exit successfully:

```bash
chakra-vault
chakra-vault model
```

## Summary Fields

The command prints a compact summary:

- `planned_downloads`: files missing locally and planned for download.
- `planned_redownloads`: corrupt local files planned for replacement.
- `downloaded`: missing files successfully downloaded.
- `redownloaded`: corrupt files successfully replaced.
- `skipped`: plan items that did not require download work.
- `failed`: executor actions that failed.
- `verification`: final verification status after execution.

Dry-run mode prints plan-only fields:

- `repo_id`: requested repository.
- `revision`: requested revision, or `default` when omitted.
- `dry_run`: `true` for plan-only output.
- `planned_downloads`: missing files that would be downloaded.
- `planned_redownloads`: corrupt files that would be replaced.
- `skipped`: files already verified.
- `unverified`: files kept because metadata is not pinned.
- `extra`: local files not present in expected metadata.
- `remote_metadata_missing`: expected files missing usable remote metadata.
- `planned_download_bytes`: known bytes that would be downloaded, or `unknown`.

## Exit Codes

- `0`: workflow completed and no executor actions failed.
- non-zero: argument parsing failed, the workflow raised an error, or one or
  more executor actions failed.

## Privacy

Workflow and planning exceptions are displayed as generic CLI errors:

```text
error: model download failed
```

```text
error: model download planning failed
```

Raw token values, provider URLs, provider exception details, and private local
paths from exceptions are not printed by the CLI.
