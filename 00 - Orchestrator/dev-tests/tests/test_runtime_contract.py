from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


def _module_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _pipeline_root() -> Path:
    return _module_root() / "orchestrator" / "pipeline"


def _package_root() -> Path:
    return _module_root() / "orchestrator"


def _bootstrap_root() -> Path:
    return _module_root() / "orchestrator" / "bootstrap"


def _tests_root() -> Path:
    return _module_root() / "dev-tests" / "tests"


def _run_batch(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["cmd.exe", "/c", "call", str(script), *arguments],
        cwd=script.parent,
        capture_output=True,
        text=True,
        check=False,
    )


LEGACY_LOC_EXCEPTIONS = {
    "model_catalog/types.py",
    "models/runtime_settings_types.py",
    "orchestrator_contract/workflow.py",
    "pipeline/release_workflow.py",
    "pipeline/record_repository.py",
    "pipeline/stage_scheduler.py",
    "ui/dialogs.py",
    "ui/model_settings_layout.py",
    "ui/repository.py",
    "ui/status_layout.py",
    "ui/workflow.py",
    "test_contract.py",
    "test_integrations_workflow_stage_calls.py",
    "test_model_catalog.py",
    "test_model_catalog_ui.py",
    "test_model_settings_layout.py",
    "test_pipeline_input_flow.py",
    "test_ui_repository.py",
    "test_worker_process.py",
}


def _assert_package_files_stay_under_200_loc(package_root: Path) -> None:
    for file_path in package_root.rglob("*.py"):
        relative = file_path.relative_to(package_root).as_posix()
        if relative in LEGACY_LOC_EXCEPTIONS:
            continue
        assert len(file_path.read_text(encoding="utf-8").splitlines()) <= 200, file_path.name


def _assert_python_files_do_not_exceed_depth(package_root: Path, *, max_depth: int) -> None:
    for file_path in package_root.rglob("*.py"):
        relative = file_path.relative_to(package_root)
        if "__pycache__" in relative.parts:
            continue
        assert len(relative.parts) <= max_depth, relative


def _assert_import_audit(package_root: Path) -> None:
    allowed_roots = set(sys.stdlib_module_names) | {"__future__", "orchestrator"}
    for file_path in package_root.rglob("*.py"):
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root in allowed_roots, f"{file_path}: unerlaubter Import {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    continue
                module = node.module or ""
                root = module.split(".")[0]
                assert root in allowed_roots, f"{file_path}: unerlaubter Import {module}"


def test_manifest_and_scripts_point_to_orchestrator_contract() -> None:
    module_root = _module_root()
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    run_script = (module_root / "run.bat").read_text(encoding="utf-8")
    build_installer_script = (module_root / "build-installer.bat").read_text(encoding="utf-8")

    assert manifest["module_key"] == "orchestrator"
    assert manifest["contract_module"] == "orchestrator.orchestrator_contract"
    assert manifest["admin_contract_module"] == "orchestrator.admin_contract"
    assert manifest["admin_actions"] == [
        "inspect_runtime",
        "manage_runtime_settings",
        "manage_credentials",
        "reveal_secret",
    ]
    assert manifest["actions"] == [
        "run",
        "reset",
        "reset_pipeline_logs",
        "embeddings",
        "activate_corpus_context",
        "inspect_source_document_sample",
        "kernel_llm_runtime_profile",
        "kernel_llm_generate",
        "healthcheck",
        "create_artifact_tree",
        "validate_artifact_tree",
        "create_pipeline_batch_manifest",
        "finalize_pipeline_batch_manifest",
    ]
    assert "-m orchestrator" in run_script
    assert 'tools\\build-installer.py' in build_installer_script
    assert '--module "00 - Orchestrator"' in build_installer_script


def test_public_surfaces_use_packages_instead_of_single_files() -> None:
    module_root = _module_root() / "orchestrator"

    assert (module_root / "credentials" / "__init__.py").exists()
    assert (module_root / "main" / "__init__.py").exists()
    assert (module_root / "orchestrator_contract" / "__init__.py").exists()
    assert (module_root / "ui" / "surface.py").exists()
    assert not (module_root / "main.py").exists()
    assert not (module_root / "orchestrator_contract.py").exists()
    assert not (module_root / "ui" / "app").exists()
    assert not (_tests_root() / "pipeline_support").exists()


def test_python_files_stay_under_200_loc() -> None:
    _assert_package_files_stay_under_200_loc(_package_root())
    _assert_package_files_stay_under_200_loc(_tests_root())


def test_product_and_test_trees_stay_flat() -> None:
    _assert_python_files_do_not_exceed_depth(_package_root(), max_depth=2)
    _assert_python_files_do_not_exceed_depth(_tests_root(), max_depth=1)


def test_import_audit_allows_only_stdlib_and_local() -> None:
    _assert_import_audit(_pipeline_root())
    _assert_import_audit(_bootstrap_root())


def test_runtime_manifest_tracks_bootstrap_surface() -> None:
    runtime_manifest = json.loads(
        (_module_root() / "runtime" / "runtime-manifest.json").read_text(encoding="utf-8")
    )

    assert "config/route_intake_policy.json" in runtime_manifest["required_files"]
    assert "config/execution_policy.json" in runtime_manifest["required_files"]
    assert "config/health_dependency_policy.json" in runtime_manifest["required_files"]
    assert "config/artifact_publication_policy.json" in runtime_manifest["required_files"]
    assert "orchestrator/orchestrator_contract/__init__.py" in runtime_manifest["required_files"]
    assert "orchestrator/orchestrator_contract/kernel_llm.py" in runtime_manifest["required_files"]
    assert "orchestrator/orchestrator_contract/workflow.py" in runtime_manifest["required_files"]
    assert "orchestrator/orchestrator_contract/validation.py" in runtime_manifest["required_files"]
    assert "orchestrator/admin_contract/__init__.py" in runtime_manifest["required_files"]
    assert "orchestrator/admin_contract/workflow.py" in runtime_manifest["required_files"]
    assert "orchestrator/edit_contract/__main__.py" in runtime_manifest["required_files"]
    assert "orchestrator/edit_contract/workflow.py" in runtime_manifest["required_files"]
    assert "orchestrator/state/__init__.py" in runtime_manifest["required_files"]
    assert "orchestrator/state/adapter.py" in runtime_manifest["required_files"]
    assert "orchestrator/state/repository.py" in runtime_manifest["required_files"]
    assert "orchestrator/bootstrap/runtime_report.py" in runtime_manifest["required_files"]
    assert "orchestrator/debug_host/process_lifecycle.py" in runtime_manifest["required_files"]
    assert "orchestrator/debug_host/workflow.py" in runtime_manifest["required_files"]
    assert "orchestrator/ui/debug_layout.py" in runtime_manifest["required_files"]
    assert "check-runtime.bat" in runtime_manifest["required_files"]
    assert "module-registry.json" in runtime_manifest["required_files"]


def test_check_runtime_script_reports_portable_runtime() -> None:
    completed = _run_batch(_module_root() / "check-runtime.bat")
    assert completed.returncode == 0, completed.stderr or completed.stdout

    payload = json.loads(completed.stdout)
    runtime_root = str((_module_root() / "runtime" / "python").resolve()).lower()

    assert payload["ok"] is True
    assert payload["python"]["path"].lower().endswith("runtime\\python\\python.exe")
    assert payload["provenance"]["customtkinter"].lower().startswith(runtime_root)
