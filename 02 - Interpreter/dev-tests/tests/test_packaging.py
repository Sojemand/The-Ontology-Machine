from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from llm_interpreter.edit_contract.env_repository import ENV_FIELD_ORDER

MODULE_ROOT = Path(__file__).parent.parent.parent
RUNTIME_ROOT = MODULE_ROOT / "runtime" / "python"
RUNTIME_MANIFEST = MODULE_ROOT / "runtime" / "runtime-manifest.json"
CHECK_RUNTIME = MODULE_ROOT / "check-runtime.bat"
INSTALLER = MODULE_ROOT / "installer.bat"
BUILD_INSTALLER = MODULE_ROOT / "build-installer.bat"
DIST_ROOT = MODULE_ROOT / "dist"
STAGE_ROOT = DIST_ROOT / "stage"


def _run_command(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def _run_batch(script: Path, *arguments: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return _run_command(["cmd.exe", "/c", "call", str(script), *arguments], cwd=cwd, env=env)


def test_runtime_checker_reports_portable_runtime() -> None:
    completed = _run_batch(CHECK_RUNTIME, cwd=MODULE_ROOT)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["python"]["path"].lower().endswith("runtime\\python\\python.exe")


def test_runtime_manifest_exists_and_points_to_runtime_surface() -> None:
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["python_version"] == "3.11"
    assert "llm_interpreter/orchestrator_contract/__main__.py" in manifest["required_files"]
    assert "llm_interpreter/edit_contract/__main__.py" in manifest["required_files"]
    assert "llm_interpreter/edit_contract/write_surface.py" in manifest["required_files"]
    assert "llm_interpreter/prompts/schema.py" in manifest["required_files"]
    assert "llm_interpreter/runtime_paths.py" in manifest["required_files"]
    assert "llm_interpreter/runtime_support.py" in manifest["required_files"]
    assert "check-runtime.bat" in manifest["required_files"]


def test_env_example_tracks_edit_contract_fields() -> None:
    env_text = (MODULE_ROOT / ".env.example").read_text(encoding="utf-8")
    fields = [line.partition("=")[0] for line in env_text.splitlines() if line.strip()]

    assert fields == list(ENV_FIELD_ORDER)


def test_installer_checkonly_validates_source_slot_without_localappdata() -> None:
    env = os.environ.copy()
    env.pop("LOCALAPPDATA", None)
    env.pop("LocalAppData", None)

    completed = _run_batch(INSTALLER, "-CheckOnly", cwd=MODULE_ROOT, env=env)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["runtime"]["ok"] is True


def test_installer_requires_localappdata_without_install_root() -> None:
    env = os.environ.copy()
    env.pop("LOCALAPPDATA", None)
    env.pop("LocalAppData", None)

    completed = _run_batch(INSTALLER, cwd=MODULE_ROOT, env=env)

    assert completed.returncode != 0
    assert "LOCALAPPDATA ist nicht gesetzt" in (completed.stderr or completed.stdout)


def test_installer_rejects_custom_root_that_is_not_app_directory(tmp_path) -> None:
    unsafe_root = tmp_path / "portable-install"
    unsafe_root.mkdir()
    marker = unsafe_root / "keep.txt"
    marker.write_text("do not delete", encoding="utf-8")

    completed = _run_batch(INSTALLER, "-InstallRoot", str(unsafe_root), cwd=MODULE_ROOT)

    assert completed.returncode != 0
    assert "InstallRoot muss auf einen app-Ordner zeigen" in (completed.stderr or completed.stdout)
    assert marker.read_text(encoding="utf-8") == "do not delete"


def test_installer_creates_portable_install_and_preserves_mutable_state(tmp_path) -> None:
    app_home = tmp_path / "portable-install"
    install_root = app_home / "app"

    install = _run_batch(INSTALLER, "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert install.returncode == 0, install.stderr or install.stdout
    assert (install_root / "runtime" / "runtime-manifest.json").exists()
    assert (app_home / "config" / ".env").exists()
    assert (app_home / "config" / "prompt_bundle" / "system_prompt.md").exists()
    assert (app_home / "config" / "prompt_bundle" / "output_schema.json").exists()
    assert (app_home / "state").exists()
    assert (app_home / "logs").exists()
    assert "OPENAI_API_KEY" not in (app_home / "config" / ".env").read_text(encoding="utf-8")
    assert "OPENAI_API_BASE_URL=https://api.openai.com/v1" in (app_home / "config" / ".env").read_text(encoding="utf-8")
    assert "LLM_MODEL" not in (app_home / "config" / ".env").read_text(encoding="utf-8")
    assert "THINKING_EFFORT" not in (app_home / "config" / ".env").read_text(encoding="utf-8")
    assert not (install_root / "run.bat").exists()
    assert not (install_root / "build-runtime.bat").exists()

    keep_state = app_home / "state" / "keep.txt"
    keep_state.write_text("persist", encoding="utf-8")
    reinstall = _run_batch(INSTALLER, "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert reinstall.returncode == 0, reinstall.stderr or reinstall.stdout
    assert keep_state.read_text(encoding="utf-8") == "persist"

    installed_check = _run_batch(install_root / "check-runtime.bat", cwd=install_root)
    assert installed_check.returncode == 0, installed_check.stderr or installed_check.stdout
    assert (install_root / "llm_interpreter" / "orchestrator_contract" / "__main__.py").exists()
    assert (install_root / "llm_interpreter" / "edit_contract" / "__main__.py").exists()
    assert (install_root / "llm_interpreter" / "edit_contract" / "write_surface.py").exists()


def test_build_installer_stage_uses_portable_contracts() -> None:
    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    try:
        stage = _run_batch(BUILD_INSTALLER, "--skip-runtime-build", cwd=MODULE_ROOT)
        assert stage.returncode == 0, stage.stderr or stage.stdout
        release_manifest = json.loads((STAGE_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        assert release_manifest["mutable_dirs"] == ["config", "state", "output", "logs", ".appdata"]
        assert release_manifest["excluded_runtime_paths"] == ["runtime\\wheelhouse"]
        assert "build-installer.bat" not in release_manifest["sign_targets"]
        assert "run.bat" not in release_manifest["sign_targets"]
        assert not (STAGE_ROOT / "run.bat").exists()
        assert not (STAGE_ROOT / "build-runtime.bat").exists()
        assert (STAGE_ROOT / "tools" / "build-runtime.bat").exists()
    finally:
        shutil.rmtree(DIST_ROOT, ignore_errors=True)
