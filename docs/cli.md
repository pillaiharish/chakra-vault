# CLI

Chakra Vault exposes a thin command-line adapter for the existing model download
workflow.

```bash
chakra-vault model download \
  --repo-id Qwen/Qwen2.5-0.5B-Instruct \
  --target-dir /tmp/chakra-vault-model \
  --revision main
```

## Arguments

- `--repo-id`: Hugging Face model repository identifier, such as
  `Qwen/Qwen2.5-0.5B-Instruct`.
- `--target-dir`: local directory where the workflow verifies existing files and
  where the safe executor promotes downloaded files.
- `--revision`: optional model revision, branch, tag, or commit.

## Summary Fields

The command prints a compact summary:

- `planned_downloads`: files missing locally and planned for download.
- `planned_redownloads`: corrupt local files planned for replacement.
- `downloaded`: missing files successfully downloaded.
- `redownloaded`: corrupt files successfully replaced.
- `skipped`: plan items that did not require download work.
- `failed`: executor actions that failed.
- `verification`: final verification status after execution.

## Exit Codes

- `0`: workflow completed and no executor actions failed.
- non-zero: argument parsing failed, the workflow raised an error, or one or
  more executor actions failed.

## Privacy

Workflow exceptions are displayed as a generic CLI error:

```text
error: model download failed
```

Raw token values, provider exception details, and private local paths from
exceptions are not printed by the CLI.
