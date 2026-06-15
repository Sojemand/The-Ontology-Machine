from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
BUILD_INSTALLER = MODULE_ROOT / "build-installer.bat"
DIST_ROOT = MODULE_ROOT / "dist"
STAGE_ROOT = DIST_ROOT / "stage"
INSTALLER_SCRIPT = MODULE_ROOT / "installer" / "OrchestratorVision.iss"
ACTIONS_BY_MODULE = {
    "optimizer": ["classify_document", "extract_document", "healthcheck"],
    "interpreter": ["interpret_document", "healthcheck", "debug_run", "generate_llm"],
    "validator": ["validate_document", "healthcheck", "debug_run"],
    "normalizer": ["normalize_document", "build_projection_catalog", "build_runtime_semantic_assets", "healthcheck", "debug_run"],
    "corpus_builder": ["load_document", "activate_semantic_release", "read_active_semantic_release", "generate_embeddings", "healthcheck", "scan_debug_input", "debug_run"],
}


def _run_batch(script: Path, *arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["cmd.exe", "/c", "call", str(script), *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _runtime_env(module_root: Path) -> dict[str, str]:
    runtime_dir = module_root / "runtime" / "python"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONHOME"] = str(runtime_dir)
    env["PYTHONPATH"] = ""
    tcl_dir = runtime_dir / "tcl"
    if (tcl_dir / "tcl8.6").exists():
        env["TCL_LIBRARY"] = str((tcl_dir / "tcl8.6").resolve())
    if (tcl_dir / "tk8.6").exists():
        env["TK_LIBRARY"] = str((tcl_dir / "tk8.6").resolve())
    return env


def _run_startup_report(module_root: Path) -> dict[str, object]:
    python_exe = module_root / "runtime" / "python" / "python.exe"
    completed = subprocess.run(
        [
            str(python_exe),
            "-m",
            "orchestrator.bootstrap.runtime_report",
            "--root",
            str(module_root),
            "--mode",
            "startup",
        ],
        cwd=module_root,
        env=_runtime_env(module_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "payload": json.loads(completed.stdout),
        "stderr": completed.stderr,
    }


def _write_sibling_stub(module_root: Path, *, module_key: str, actions: list[str]) -> None:
    runtime_dir = module_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "python.exe").write_text("", encoding="utf-8")
    manifest = {
        "module_key": module_key,
        "display_name": module_key,
        "contract_version": 1,
        "runtime_dir": "runtime/python",
        "contract_module": f"{module_key}.orchestrator_contract",
        "launcher_module": module_key,
        "actions": actions,
        "external_dependencies": [],
    }
    (module_root / "module-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_installer_script_uses_per_user_module_slot() -> None:
    script = INSTALLER_SCRIPT.read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in script
    assert r"DefaultDirName={localappdata}\Programs\Vision Pipeline\00 - Orchestrator" in script
    assert 'Name: "{app}\\state"; Flags: uninsneveruninstall' in script
    assert 'Name: "{app}\\config"; Flags: uninsneveruninstall' in script
    assert 'Excludes: "config\\*"' in script
    assert 'Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist' in script


def test_build_installer_stage_and_install_slot_contracts(tmp_path: Path) -> None:
    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    try:
        stage = _run_batch(BUILD_INSTALLER, "--skip-runtime-build", cwd=MODULE_ROOT)
        assert stage.returncode == 0, stage.stderr or stage.stdout

        release_manifest = json.loads((STAGE_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        assert release_manifest["mutable_dirs"] == ["state"]
        assert release_manifest["mutable_files"] == []
        assert release_manifest["excluded_runtime_paths"] == ["runtime\\wheelhouse"]
        assert release_manifest["sign_targets"] == [
            "run.bat",
            "check-runtime.bat",
            "module-manifest.json",
            "module-registry.json",
            "runtime\\runtime-manifest.json",
        ]
        assert (STAGE_ROOT / "run.bat").exists()
        assert (STAGE_ROOT / "check-runtime.bat").exists()
        assert (STAGE_ROOT / "config" / "route_intake_policy.json").exists()
        assert (STAGE_ROOT / "config" / "execution_policy.json").exists()
        assert (STAGE_ROOT / "config" / "health_dependency_policy.json").exists()
        assert (STAGE_ROOT / "config" / "artifact_publication_policy.json").exists()
        assert not (STAGE_ROOT / "state").exists()
        assert not list(STAGE_ROOT.rglob("credentials_state.json"))
        assert not list(STAGE_ROOT.rglob("keystore.enc"))
        assert not (STAGE_ROOT / "runtime" / "wheelhouse").exists()
        assert not (STAGE_ROOT / "installer").exists()

        install_root = tmp_path / "Vision Pipeline" / "00 - Orchestrator"
        shutil.copytree(STAGE_ROOT, install_root)

        runtime_check = _run_batch(install_root / "check-runtime.bat", cwd=install_root)
        assert runtime_check.returncode == 0, runtime_check.stderr or runtime_check.stdout
        assert json.loads(runtime_check.stdout)["ok"] is True

        isolated = _run_startup_report(install_root)
        assert isolated["returncode"] == 1
        assert isolated["payload"]["runtime"]["ok"] is True
        assert isolated["payload"]["federation"]["ok"] is False
        assert "Module path is missing for optimizer" in isolated["payload"]["error"]

        registry = json.loads((install_root / "module-registry.json").read_text(encoding="utf-8"))
        for module_key, entry in registry["modules"].items():
            sibling_root = (install_root / Path(entry["path"])).resolve()
            _write_sibling_stub(sibling_root, module_key=module_key, actions=ACTIONS_BY_MODULE[module_key])

        startup_ok = _run_startup_report(install_root)
        assert startup_ok["returncode"] == 0, startup_ok["stderr"]
        assert startup_ok["payload"]["ok"] is True
        assert startup_ok["payload"]["federation"]["ok"] is True
        assert [item["key"] for item in startup_ok["payload"]["federation"]["resolved_modules"]] == [
            "optimizer",
            "interpreter",
            "validator",
            "normalizer",
            "corpus_builder",
        ]
    finally:
        shutil.rmtree(DIST_ROOT, ignore_errors=True)


def test_runtime_manifest_tracks_policy_config_and_edit_contract() -> None:
    runtime_manifest = json.loads((MODULE_ROOT / "runtime" / "runtime-manifest.json").read_text(encoding="utf-8"))
    required = set(runtime_manifest["required_files"])

    assert "config/route_intake_policy.json" in required
    assert "config/execution_policy.json" in required
    assert "config/health_dependency_policy.json" in required
    assert "config/artifact_publication_policy.json" in required
    assert "orchestrator/edit_contract/__main__.py" in required
    assert "orchestrator/edit_contract/describe_surfaces.py" in required
    assert "orchestrator/edit_contract/descriptor_metadata.py" in required
    assert "orchestrator/edit_contract/summary_cards.py" in required
    assert "orchestrator/edit_contract/write_surface.py" in required

