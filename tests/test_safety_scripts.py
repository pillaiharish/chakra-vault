from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_script(name: str, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *[str(arg) for arg in args]],
        capture_output=True,
        check=False,
        text=True,
    )


def test_safety_scripts_are_importable() -> None:
    for name in (
        "check_no_large_files.py",
        "check_no_hf_upload.py",
        "check_no_private_paths.py",
    ):
        module = load_script(name)
        assert callable(module.main)


def test_large_file_check_blocks_files_over_limit(tmp_path: Path) -> None:
    (tmp_path / "small.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "large.txt").write_bytes(b"x" * 16)

    result = run_script("check_no_large_files.py", "--max-bytes", "8", tmp_path)

    assert result.returncode == 1
    assert "large.txt" in result.stderr


def test_large_file_check_allows_files_under_limit(tmp_path: Path) -> None:
    (tmp_path / "small.txt").write_text("ok", encoding="utf-8")

    result = run_script("check_no_large_files.py", "--max-bytes", "8", tmp_path)

    assert result.returncode == 0


def test_hf_upload_check_blocks_publish_apis(tmp_path: Path) -> None:
    unsafe = "from huggingface_hub import HfApi\nHfApi()." + "upload" + "_folder('out')\n"
    (tmp_path / "publish.py").write_text(unsafe, encoding="utf-8")

    result = run_script("check_no_hf_upload.py", tmp_path)

    assert result.returncode == 1
    assert "publish.py" in result.stderr


def test_hf_upload_check_allows_read_only_text(tmp_path: Path) -> None:
    safe = "from huggingface_hub import snapshot_download\nsnapshot_download('org/model')\n"
    (tmp_path / "read_only.py").write_text(safe, encoding="utf-8")

    result = run_script("check_no_hf_upload.py", tmp_path)

    assert result.returncode == 0


def test_private_path_check_blocks_user_paths(tmp_path: Path) -> None:
    mac_path = "/" + "Users" + "/" + "person" + "/" + "secret.txt"
    linux_path = "/" + "home" + "/" + "person" + "/" + "secret.txt"
    windows_path = "C:" + "\\" + "Users" + "\\" + "person" + "\\" + "secret.txt"
    (tmp_path / "paths.txt").write_text(
        "\n".join([mac_path, linux_path, windows_path]),
        encoding="utf-8",
    )

    result = run_script("check_no_private_paths.py", tmp_path)

    assert result.returncode == 1
    assert "paths.txt" in result.stderr


def test_private_path_check_allows_relative_paths(tmp_path: Path) -> None:
    (tmp_path / "manifest.txt").write_text("models/example/config.json\n", encoding="utf-8")

    result = run_script("check_no_private_paths.py", tmp_path)

    assert result.returncode == 0
