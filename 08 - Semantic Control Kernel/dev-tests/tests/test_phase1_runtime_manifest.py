from __future__ import annotations

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]


def _load_json(relative_path: str) -> dict[str, object]:
    with (MODULE_ROOT / relative_path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return payload


def _installable_requirements(relative_path: str) -> list[str]:
    entries: list[str] = []
    for raw_line in (MODULE_ROOT / relative_path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def test_module_manifest_matches_active_runtime_contract_surface() -> None:
    manifest = _load_json("module-manifest.json")

    assert manifest["module_key"] == "semantic_control_kernel"
    assert manifest["runtime_dir"] == "runtime/python"
    assert manifest["launcher_module"] == "semantic_control_kernel"
    assert manifest["contract_module"] == "semantic_control_kernel.orchestrator_contract"
    assert isinstance(manifest["actions"], list)
    assert "healthcheck" not in manifest["actions"]


def test_runtime_manifest_matches_active_runtime_contract() -> None:
    module_manifest = _load_json("module-manifest.json")
    runtime_manifest = _load_json("runtime/runtime-manifest.json")

    assert runtime_manifest["module_key"] == "semantic_control_kernel"
    assert runtime_manifest["status"] == module_manifest["status"]
    assert runtime_manifest["contract_version"] == module_manifest["contract_version"]
    assert runtime_manifest["runtime_kind"] == "python"
    assert runtime_manifest["runtime_path"] == "runtime/python"
    assert runtime_manifest["python_version"] == "3.11"
    assert runtime_manifest["build_status"] == "buildable"
    assert runtime_manifest["normal_operation_requires_host_python"] is False
    assert runtime_manifest["runtime_builder"] == "root_tools_build_runtimes"
    assert runtime_manifest["runtime_check_module"] == "semantic_control_kernel.bootstrap.runtime_report"


def test_phase1_runtime_has_no_installable_product_dependencies() -> None:
    assert _installable_requirements("requirements.txt") == []


def test_phase1_build_runtime_wrapper_delegates_to_root_builder() -> None:
    script = (MODULE_ROOT / "build-runtime.bat").read_text(encoding="utf-8")

    assert 'call "%~dp0..\\tools\\build-runtimes.bat" --module "08 - Semantic Control Kernel" %*' in script


def test_phase1_dev_test_lockfile_uses_root_wheelhouse_pins() -> None:
    assert _installable_requirements("dev-tests/requirements.lock.txt") == [
        "colorama==0.4.6",
        "iniconfig==2.3.0",
        "packaging==26.0",
        "py==0.0.0",
        "pluggy==1.6.0",
        "Pygments==2.19.2",
        "pytest==9.0.2",
    ]


def test_phase1_drift_preflight_records_build_plan_authority() -> None:
    payload = _load_json("dev-tests/fixtures/phase1_drift_preflight.json")

    assert payload["drift_preflight"] == "build_plan_authority_applied"
    assert payload["authority"] == "SPEC_Semantic_Control_Kernel_Build.md"
