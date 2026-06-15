from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from conftest import MODULE_ROOT

BUILD_INSTALLER = MODULE_ROOT / "build-installer.bat"
CHECK_RUNTIME = MODULE_ROOT / "check-runtime.bat"
MODULE_MANIFEST = MODULE_ROOT / "module-manifest.json"
RUNTIME_MANIFEST = MODULE_ROOT / "runtime" / "runtime-manifest.json"
INSTALLER_MANIFEST = MODULE_ROOT / "installer" / "installer-manifest.json"
STAGE_ROOT = MODULE_ROOT / "dist" / "stage"
RUNTIME_PYTHON_EXCLUSIONS: set[str] = set()


def _run_batch(script: Path, *arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["cmd.exe", "/c", "call", str(script), *arguments], cwd=cwd, capture_output=True, text=True, check=False)


def test_manifests_and_installer_contract_are_aligned() -> None:
    manifest = json.loads(MODULE_MANIFEST.read_text(encoding="utf-8"))
    runtime_manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    installer_manifest = json.loads(INSTALLER_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["launcher_module"] == "edit_suite"
    assert manifest["contract_module"] == "edit_suite.orchestrator_contract"
    assert manifest["actions"] == ["healthcheck"]
    assert "edit_suite/contract_runtime/adapter.py" in runtime_manifest["required_files"]
    assert "edit_suite/registry/workflow.py" in runtime_manifest["required_files"]
    assert "edit_suite/registry/contract_probe.py" in runtime_manifest["required_files"]
    assert "edit_suite/surfaces/contract_client.py" in runtime_manifest["required_files"]
    assert "edit_suite/surfaces/load_bundle.py" in runtime_manifest["required_files"]
    assert "edit_suite/surfaces/section_assignment.py" in runtime_manifest["required_files"]
    assert "edit_suite/surfaces/sections.py" in runtime_manifest["required_files"]
    assert "edit_suite/surfaces/summary_builder.py" in runtime_manifest["required_files"]
    assert "edit_suite/surfaces/workflow.py" in runtime_manifest["required_files"]
    assert "edit_suite/ui/section_intro.py" in runtime_manifest["required_files"]
    assert "edit_suite/ui/nested_policy_editor.py" in runtime_manifest["required_files"]
    assert "edit_suite/ui/surface_cards.py" in runtime_manifest["required_files"]
    assert "edit_suite/ui/operation_progress.py" in runtime_manifest["required_files"]
    assert "edit_suite/ui/text_widgets.py" in runtime_manifest["required_files"]
    assert "edit_suite/ui/view_model.py" in runtime_manifest["required_files"]
    assert "edit_suite/bootstrap/runtime_report.py" in runtime_manifest["required_files"]
    assert installer_manifest["mutable_dirs"] == ["state"]


def test_runtime_checker_and_installer_stage_work_with_local_runtime() -> None:
    runtime_check = _run_batch(CHECK_RUNTIME, cwd=MODULE_ROOT)
    assert runtime_check.returncode == 0, runtime_check.stderr or runtime_check.stdout
    shutil.rmtree(STAGE_ROOT.parent, ignore_errors=True)
    try:
        stage = _run_batch(BUILD_INSTALLER, "--skip-runtime-build", cwd=MODULE_ROOT)
        assert stage.returncode == 0, stage.stderr or stage.stdout
        release_manifest = json.loads((STAGE_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        assert release_manifest["mutable_dirs"] == ["state"]
        assert not (STAGE_ROOT / "state").exists()
    finally:
        shutil.rmtree(STAGE_ROOT.parent, ignore_errors=True)


def test_runtime_manifest_covers_all_product_python_sources() -> None:
    runtime_manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    required_files = {item.replace("\\", "/") for item in runtime_manifest["required_files"]}
    product_sources = {
        str(path.relative_to(MODULE_ROOT)).replace("\\", "/")
        for path in (MODULE_ROOT / "edit_suite").rglob("*.py")
    }

    missing = sorted(product_sources - required_files - RUNTIME_PYTHON_EXCLUSIONS)

    assert missing == []
