from __future__ import annotations

import json
import subprocess
from pathlib import Path


MODULE_ROOT = Path(__file__).parent.parent.parent
RUNTIME_ROOT = MODULE_ROOT / "runtime" / "python"
RUNTIME_PYTHON = RUNTIME_ROOT / "python.exe"
CHECK_RUNTIME = MODULE_ROOT / "check-runtime.bat"
INSTALLER = MODULE_ROOT / "installer.bat"
INSTALLER_ALIAS = MODULE_ROOT / "install-user.bat"
RUNTIME_MANIFEST = MODULE_ROOT / "runtime" / "runtime-manifest.json"
MODULE_MANIFEST = MODULE_ROOT / "module-manifest.json"
INSTALLER_MANIFEST = MODULE_ROOT / "installer" / "installer-manifest.json"


def _run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def _run_batch(script: Path, *arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run_command(["cmd.exe", "/c", "call", str(script), *arguments], cwd=cwd)


def test_bundled_runtime_provenance_is_self_contained():
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    completed = _run_command(
        [
            str(RUNTIME_PYTHON),
            "-c",
            "import encodings, json, requests, sys, yaml; "
            "print(json.dumps({'version': sys.version.split()[0], 'encodings': encodings.__file__, 'requests': requests.__file__, 'yaml': yaml.__file__}))",
        ],
        cwd=MODULE_ROOT,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    runtime_root = str(RUNTIME_ROOT.resolve()).lower()
    assert payload["version"].startswith(manifest["python_version"])
    assert payload["encodings"].lower().startswith(runtime_root)
    assert payload["requests"].lower().startswith(runtime_root)
    assert payload["yaml"].lower().startswith(runtime_root)


def test_runtime_checker_reports_portable_runtime():
    before = set(RUNTIME_ROOT.glob(".runtime-check-*.py"))
    completed = _run_batch(CHECK_RUNTIME, cwd=MODULE_ROOT)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["python"]["path"].lower().endswith("runtime\\python\\python.exe")
    assert payload["provenance"]["requests"].lower().startswith(str(RUNTIME_ROOT.resolve()).lower())
    assert set(RUNTIME_ROOT.glob(".runtime-check-*.py")) == before


def test_manifest_keeps_launcher_and_contract_surface_aligned():
    manifest = json.loads(MODULE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["launcher_module"] == "normalizer_vision"
    assert manifest["contract_module"] == "normalizer_vision.orchestrator_contract"
    assert manifest["actions"] == [
        "normalize_document",
        "build_projection_catalog",
        "build_runtime_semantic_assets",
        "publish_semantic_release",
        "list_default_blueprints",
        "export_default_blueprint_release",
        "create_zero_shot_working_release",
        "healthcheck",
        "debug_run",
    ]


def test_runtime_manifest_tracks_headless_package_surface():
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    assert not (MODULE_ROOT / "run.bat").exists()
    assert "vision_pipeline_shared/__init__.py" in manifest["required_files"]
    assert "vision_pipeline_shared/semantic_identity.py" in manifest["required_files"]
    assert "normalizer_vision/shared_identity.py" in manifest["required_files"]
    assert "normalizer_vision/edit_contract/__main__.py" in manifest["required_files"]
    assert "normalizer_vision/main/__init__.py" in manifest["required_files"]
    assert "normalizer_vision/orchestrator_contract/__init__.py" in manifest["required_files"]
    assert "normalizer_vision/orchestrator_contract/adapter.py" in manifest["required_files"]
    assert "normalizer_vision/orchestrator_contract/__main__.py" in manifest["required_files"]
    assert "normalizer_vision/orchestrator_contract/value_parsing.py" in manifest["required_files"]
    assert "normalizer_vision/orchestrator_contract/validation.py" in manifest["required_files"]
    assert "normalizer_vision/orchestrator_contract/workflow.py" in manifest["required_files"]
    assert "normalizer_vision/semantic_release/shared_identity.py" in manifest["required_files"]
    assert "normalizer_vision/source_authoring/minimal_custom_release.py" in manifest["required_files"]
    assert "check-runtime.bat" in manifest["required_files"]
    assert "run.bat" not in manifest["required_files"]
    assert "runtime/python/Lib/tkinter/__init__.py" not in manifest["required_files"]
    assert "runtime/python/Lib/site-packages/customtkinter/__init__.py" not in manifest["required_files"]


def test_installer_manifest_tracks_headless_slot_contract():
    manifest = json.loads(INSTALLER_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["default_install_dir"].endswith(r"Programs\Vision Pipeline\04 - Normalizer")
    assert manifest["mutable_dirs"] == ["output", "state"]
    assert manifest["mutable_globs"] == []
    assert "run.bat" not in manifest["sign_targets"]


def test_installer_check_only_validates_source_runtime(scratch_dir: Path):
    install_root = scratch_dir / "slot"
    completed = _run_batch(INSTALLER, "-CheckOnly", "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["install_root"] == str(install_root)


def test_installer_alias_forwards_to_installer(scratch_dir: Path):
    install_root = scratch_dir / "alias-slot"
    completed = _run_batch(INSTALLER_ALIAS, "-CheckOnly", "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout)["ok"] is True


def test_installer_creates_headless_portable_slot_and_cli_runs(scratch_dir: Path):
    install_root = scratch_dir / "slot"
    install = _run_batch(INSTALLER, "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert install.returncode == 0, install.stderr or install.stdout
    assert (install_root / "runtime" / "runtime-manifest.json").exists()
    assert not (install_root / "run.bat").exists()
    assert not (install_root / "runtime" / "wheelhouse").exists()
    assert not (install_root / ".env").exists()

    installed_check = _run_batch(install_root / "check-runtime.bat", cwd=install_root)
    assert installed_check.returncode == 0, installed_check.stderr or installed_check.stdout

    for command in (["check-config"], ["analyze-taxonomy"]):
        completed = _run_command(
            [str(install_root / "runtime" / "python" / "python.exe"), "-m", "normalizer_vision", *command],
            cwd=install_root,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout


def test_installer_reinstall_preserves_mutable_state_without_ui_state_migration(scratch_dir: Path):
    install_root = scratch_dir / "slot"
    assert _run_batch(INSTALLER, "-InstallRoot", str(install_root), cwd=MODULE_ROOT).returncode == 0

    (install_root / "config" / "config.yaml").write_text("timeout_seconds: 99\n", encoding="utf-8")
    (install_root / "config" / "prompt_bundle.json").write_text('{"system_prompt":"preserved"}', encoding="utf-8")
    (install_root / "config" / "prompt_overrides.json").write_text('{"system_prompt":"delta"}', encoding="utf-8")
    (install_root / "config" / "semantic_release.recipe.json").write_text('{"release_id":"preserved.release"}', encoding="utf-8")
    (install_root / "output").mkdir(parents=True, exist_ok=True)
    (install_root / "output" / "result.json").write_text("{}", encoding="utf-8")
    (install_root / "state").mkdir(parents=True, exist_ok=True)
    (install_root / "state" / "note.txt").write_text("keep", encoding="utf-8")
    (install_root / "config" / "ui_state.json").write_text("{}", encoding="utf-8")

    reinstall = _run_batch(INSTALLER, "-InstallRoot", str(install_root), cwd=MODULE_ROOT)
    assert reinstall.returncode == 0, reinstall.stderr or reinstall.stdout

    assert (install_root / "config" / "config.yaml").read_text(encoding="utf-8") == "timeout_seconds: 99\n"
    assert (install_root / "output" / "result.json").exists()
    assert (install_root / "state" / "note.txt").exists()
    assert not (install_root / "config" / "ui_state.json").exists()
    assert not (install_root / "state" / "ui_state.json").exists()


def test_installer_fails_closed_on_inaccessible_install_state_helper():
    text = (MODULE_ROOT / "tools" / "installer.ps1").read_text(encoding="utf-8")
    catch_block = text.split("catch [System.UnauthorizedAccessException]", 1)[1].split("}", 1)[0]

    assert "catch [System.UnauthorizedAccessException]" in text
    assert "Zugriff verweigert beim Lesen von Installationsdaten" in catch_block
    assert "return @()" not in catch_block
