from __future__ import annotations

import json

from packaging_support import MODULE_MANIFEST, MODULE_ROOT, RUNTIME_MANIFEST


def test_manifest_keeps_debug_contract_surface_aligned() -> None:
    manifest = json.loads(MODULE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["launcher_module"] == "validator_vision"
    assert manifest["contract_module"] == "validator_vision.orchestrator_contract"
    assert manifest["edit_contract_module"] == "validator_vision.edit_contract"
    assert manifest["actions"] == ["validate_document", "healthcheck", "debug_run"]
    assert manifest["edit_surfaces"] == [
        "validator.settings",
        "validator.report_preview_policy",
        "validator.debug_capabilities",
    ]
    assert manifest["debug_surface"] == {
        "supports_batch": True,
        "supports_single": True,
        "supports_scan": False,
        "input_source": "module_selected_input",
        "output_source": "orchestrator_assigned_output",
        "controls": ["mode", "raw_evidence", "check_toggles"],
        "artifacts": ["validation_reports", "config_snapshot", "report_index"],
    }


def test_runtime_manifest_tracks_host_only_surface() -> None:
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    assert "validator_vision/main/__init__.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/__init__.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/__main__.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/describe_surfaces.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/read_surface.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/repository.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/summary.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/types.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/validation.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/validate_surface.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/workflow.py" in manifest["required_files"]
    assert "validator_vision/edit_contract/write_surface.py" in manifest["required_files"]
    assert "run.bat" not in manifest["required_files"]
    assert "runtime/python/Lib/tkinter/__init__.py" not in manifest["required_files"]
    assert "runtime/python/Lib/site-packages/customtkinter/__init__.py" not in manifest["required_files"]


def test_runtime_manifest_covers_all_product_python_sources() -> None:
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    required = set(manifest["required_files"])
    product_sources = {
        path.relative_to(MODULE_ROOT).as_posix()
        for path in (MODULE_ROOT / "validator_vision").rglob("*.py")
    }

    assert product_sources <= required
