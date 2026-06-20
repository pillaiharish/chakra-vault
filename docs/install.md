# Install

Chakra Vault is currently intended for local development installs from the
repository.

## Local Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/chakra-vault --help
```

The `chakra-vault` command is installed through the Python console script
defined in `pyproject.toml`. It is not a shell alias. The command is available
wherever the active Python environment places console scripts.

## Activated Environment

```bash
source .venv/bin/activate
chakra-vault --help
chakra-vault model download --help
```

## Windows Virtual Environment

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\chakra-vault --help
```

## Global Installs

Global installs are intentionally not the default recommendation yet. `pipx`
usage and published package installation can be documented after packaging and
release workflows are stable.

## Not Included Yet

- systemd service
- macOS launchd service
- Windows service
- Homebrew, winget, or choco installer
- shell completion
- daemon mode

Service installation should come after configuration, a ledger, and background
jobs exist.
