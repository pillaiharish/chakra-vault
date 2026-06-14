# No Hugging Face Upload Policy

Chakra Vault must not upload, push, publish, create repositories, delete
repositories, or delete remote files on Hugging Face Hub.

PR 1 contains static policy and repository safety checks only. It does not add a
download engine or Hugging Face client implementation.

## Forbidden Behavior

- Uploading files, folders, model cards, generated artifacts, or repositories.
- Pushing local files or commits to a Hub repository.
- Publishing, mirroring, or syncing local vault content to a remote registry.
- Creating or deleting Hub repositories.
- Deleting or mutating remote files.
- Storing Hub write tokens, private namespaces, or private repository details.

## Allowed Future Behavior

Future phases may add explicitly read-only metadata inspection or download
features. Those features must remain local-first, must not add Hub write APIs,
and must keep the static no-upload scanner in CI.
