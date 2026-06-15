from __future__ import annotations

from pathlib import Path

from edit_contract_support import _run_contract


def test_debug_capabilities_is_read_only(tmp_path: Path) -> None:
    current = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "optimizer.debug_capabilities"})
    assert current["status"] == "ok"
    assert current["value"]["operation_links"]
    rejected = _run_contract(
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "optimizer.debug_capabilities",
            "value": current["value"],
        },
    )
    assert rejected["status"] == "error"
    assert "read-only" in rejected["reason"]


def test_output_contract_preview_is_read_only_and_documents_llm_ocr_boundary(tmp_path: Path) -> None:
    current = _run_contract(tmp_path, {"action": "read_surface", "surface_id": "optimizer.output_contract_preview"})
    assert current["status"] == "ok"
    assert current["value"]["schema_version"] == "optimizer_raw_v2"
    assert current["value"]["profile_contract"]["selector_field"] == "optimizer_profile"
    assert current["value"]["llm_ocr_runtime"] == {
        "dependency": "optimizer_ocr",
        "env_prefix": "OPTIMIZER_OCR_",
        "owner": "orchestrator",
        "local_ocr_plugins": False,
        "secrets_persisted_by_optimizer": False,
    }
    rejected = _run_contract(
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "optimizer.output_contract_preview",
            "value": current["value"],
        },
    )
    assert rejected["status"] == "error"
    assert "read-only" in rejected["reason"]
