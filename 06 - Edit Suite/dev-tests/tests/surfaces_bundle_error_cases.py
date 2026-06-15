from __future__ import annotations

from pathlib import Path

from edit_suite.surfaces.sections import build_sections
from surfaces_support import bundle_workflow, entry


def test_load_bundle_keeps_other_surfaces_when_one_surface_read_fails(tmp_path: Path, monkeypatch) -> None:
    descriptors = (
        {
            "surface_id": "optimizer.settings",
            "label": "Settings",
            "kind": "settings",
            "editable": True,
            "source_path": "config/config.yaml",
            "section": "Settings",
            "field_groups": [{"label": "Execution", "fields": ["parallel_workers"]}],
        },
        {"surface_id": "optimizer.ocr_prompt", "label": "LLM-OCR Prompt", "kind": "prompt_bundle", "editable": True, "source_path": "config/optimizer_ocr_prompt.md", "section": "Prompts/Assets"},
        {"surface_id": "optimizer.output_contract_preview", "label": "Output Contract Preview", "kind": "inspection", "editable": False, "source_path": "ingestion_layer_vision/models/raw_workflow.py", "section": "Preview/Drift"},
        {"surface_id": "optimizer.debug_capabilities", "label": "Debug Capabilities", "kind": "capability_summary", "editable": False, "source_path": "module-manifest.json", "section": "Operations"},
    )
    values = {
        "optimizer.ocr_prompt": {"ocr_prompt_md": "Extract OCR for {page_count} pages."},
        "optimizer.output_contract_preview": {"schema_version": "optimizer_raw_v2"},
        "optimizer.debug_capabilities": {"operation_links": []},
    }

    def fake_invoke(entry, state_root, payload):
        del entry, state_root
        if payload["action"] == "describe_surfaces":
            return {"status": "ok", "surfaces": descriptors, "module_summary": "owner summary"}
        if payload["surface_id"] == "optimizer.settings":
            raise RuntimeError("ModuleNotFoundError: No module named 'yaml'")
        return {"status": "ok", "value": values[payload["surface_id"]]}

    monkeypatch.setattr(bundle_workflow, "invoke_contract", fake_invoke)

    bundle = bundle_workflow.load_bundle(entry(), state_root=tmp_path)
    sections = {section.name: section for section in build_sections(entry(), bundle, {})}

    assert len(bundle.surfaces) == 4
    assert bundle.module_summary == "owner summary"
    assert bundle.surfaces[0].load_error
    assert bundle.surfaces[0].editable is False
    assert "yaml" in bundle.surfaces[0].load_error.lower()
    assert [surface.surface_id for surface in sections["Prompts/Assets"].surfaces] == ["optimizer.ocr_prompt"]
    assert [surface.surface_id for surface in sections["Operations"].surfaces] == ["optimizer.debug_capabilities"]
    assert sections["Preview/Drift"].surfaces[0].surface_id == "optimizer.output_contract_preview"
    assert sections["Settings"].surfaces[0].load_error
    assert any(surface.load_error for surface in sections["Preview/Drift"].surfaces)
