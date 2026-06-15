from __future__ import annotations

from edit_suite.surfaces.types import ModuleSurfaceBundle, SurfaceModel
from edit_suite.ui import view_model
from view_model_support import entry


def test_detail_view_maps_optimizer_surfaces_into_expected_sections() -> None:
    optimizer_entry = entry("01 - Optimizer", "ready")
    bundle = ModuleSurfaceBundle(
        source="contract",
        surfaces=(
            SurfaceModel("optimizer.settings", "Settings", "settings", True, "form", {}, {"parallel_workers": 1, "render_dpi": 150}, {"parallel_workers": 1, "render_dpi": 150}, ()),
            SurfaceModel(
                "optimizer.ocr_prompt",
                "LLM-OCR Prompt",
                "prompt_bundle",
                True,
                "prompt_bundle",
                {"section": "Prompts/Assets"},
                {"ocr_prompt_md": "Extract OCR for {page_count} pages."},
                {"ocr_prompt_md": "Extract OCR for {page_count} pages."},
                (),
            ),
            SurfaceModel(
                "optimizer.output_contract_preview",
                "Output Contract Preview",
                "inspection",
                False,
                "json",
                {"section": "Preview/Drift"},
                {"schema_version": "optimizer_raw_v2", "llm_ocr_runtime": {"dependency": "optimizer_ocr"}},
                {"schema_version": "optimizer_raw_v2", "llm_ocr_runtime": {"dependency": "optimizer_ocr"}},
                (),
            ),
            SurfaceModel("optimizer.debug_capabilities", "Debug Capabilities", "capability_summary", False, "readonly", {}, {"operation_links": []}, {"operation_links": []}, ()),
        ),
        module_summary="",
    )

    detail = view_model.detail_view(optimizer_entry, bundle=bundle)
    sections = {section.name: section for section in detail.sections}

    assert "OPTIMIZER HELP" in sections["Summary"].body
    assert "This slot configures and inspects the merged Optimizer module for both vision and file profiles." in sections["Summary"].body
    assert "- max_file_size_mb: maximum accepted input size in MB." in sections["Summary"].body
    assert "Vision OCR now runs through the Orchestrator-owned `optimizer_ocr` LLM target." in sections["Summary"].body
    assert "LLM-OCR Prompt" in sections["Summary"].body
    assert "Output Contract Reference" in sections["Summary"].body
    assert "`OPTIMIZER_OCR_*` process overlay" in sections["Summary"].body
    assert "Current Status: Readiness = ready." in sections["Summary"].body
    assert [surface.surface_id for surface in sections["Settings"].surfaces] == ["optimizer.settings"]
    assert [surface.surface_id for surface in sections["Prompts/Assets"].surfaces] == ["optimizer.ocr_prompt"]
    assert [surface.surface_id for surface in sections["Operations"].surfaces] == ["optimizer.debug_capabilities"]
    assert sections["Preview/Drift"].surfaces[0].surface_id == "optimizer.output_contract_preview"
    assert len(sections["Preview/Drift"].surfaces) == 5


def test_detail_view_uses_owner_module_summary_and_descriptor_sections_for_optimizer() -> None:
    optimizer_entry = entry("01 - Optimizer", "ready")
    bundle = ModuleSurfaceBundle(
        source="contract",
        surfaces=(
            SurfaceModel("optimizer.settings", "Settings", "settings", True, "form", {"section": "Settings", "field_groups": [{"label": "Processing", "fields": ["parallel_workers"]}]}, {"parallel_workers": 1}, {"parallel_workers": 1}, ()),
            SurfaceModel("optimizer.ocr_prompt", "LLM-OCR Prompt", "prompt_bundle", True, "prompt_bundle", {"section": "Prompts/Assets"}, {"ocr_prompt_md": "Extract OCR for {page_count} pages."}, {"ocr_prompt_md": "Extract OCR for {page_count} pages."}, ()),
            SurfaceModel("optimizer.output_contract_preview", "Output Contract Preview", "inspection", False, "json", {"section": "Preview/Drift"}, {"schema_version": "optimizer_raw_v2"}, {"schema_version": "optimizer_raw_v2"}, ()),
            SurfaceModel("optimizer.debug_capabilities", "Debug Capabilities", "capability_summary", False, "readonly", {"section": "Operations"}, {"operation_links": []}, {"operation_links": []}, ()),
        ),
        module_summary="FILE OPTIMIZER HELP\nOwner summary",
    )

    detail = view_model.detail_view(optimizer_entry, bundle=bundle)
    sections = {section.name: section for section in detail.sections}

    assert sections["Summary"].body == "FILE OPTIMIZER HELP\nOwner summary"
    assert [surface.surface_id for surface in sections["Settings"].surfaces] == ["optimizer.settings"]
    assert [surface.surface_id for surface in sections["Prompts/Assets"].surfaces] == ["optimizer.ocr_prompt"]
    assert [surface.surface_id for surface in sections["Operations"].surfaces] == ["optimizer.debug_capabilities"]
    assert sections["Preview/Drift"].surfaces[0].surface_id == "optimizer.output_contract_preview"
