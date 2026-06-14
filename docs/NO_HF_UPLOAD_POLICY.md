# No Hugging Face Upload Policy

Chakra Vault must not upload, push, publish, create repos, delete repos, or
delete remote files on Hugging Face.

Allowed HF behavior:

- resolve model metadata
- read repository file lists
- download files into local storage
- compare local files against pinned remote metadata

Forbidden behavior:

- `create_repo`
- `delete_repo`
- `delete_file`
- `upload_file`
- `upload_folder`
- `push_to_hub`

The runtime policy rejects forbidden actions and the static scanner fails if
forbidden write APIs appear in source files.
# No Hub Upload Policy

Chakra Vault is designed to protect local model artifacts. It must not publish,
mirror, or push local artifacts to Hugging Face Hub or any other model registry.

## Prohibited Behavior

- Calling Hub APIs that publish files, folders, repositories, model cards, or
  generated artifacts.
- Adding CLI commands that publish local files to a Hub repository.
- Adding automated workflows that sync local vault content to a remote model
  registry.
- Storing access tokens, personal namespaces, or private repository names.

## Allowed Behavior

- Reading local metadata.
- Verifying checksums.
- Producing local manifests that do not expose private paths.
- Documenting the policy in general terms.

Any future network feature must be explicitly read-only unless a new policy and
review process is added first.
