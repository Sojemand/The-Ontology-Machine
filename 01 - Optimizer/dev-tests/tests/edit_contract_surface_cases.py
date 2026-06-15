from __future__ import annotations

from pathlib import Path

from edit_contract_support import _run_contract


def test_describe_surfaces_returns_exact_surface_set(tmp_path: Path) -> None:
    payload = _run_contract(tmp_path, {"action": "describe_surfaces"})
    assert payload["status"] == "ok"
    assert payload["module_summary"].startswith("OPTIMIZER HELP")
    assert "optimizer_raw_v2" in payload["module_summary"]
    assert "ocr_reference.blocks" in payload["module_summary"]
    assert "Output Contract Preview" in payload["module_summary"]
    assert "optimizer_ocr" in payload["module_summary"]
    assert [item["surface_id"] for item in payload["surfaces"]] == [
        "optimizer.settings",
        "optimizer.ocr_prompt",
        "optimizer.output_contract_preview",
        "optimizer.debug_capabilities",
    ]
    settings_descriptor = payload["surfaces"][0]
    assert settings_descriptor["section"] == "Settings"
    assert settings_descriptor["field_groups"] == [
        {"label": "Processing", "fields": ["max_file_size_mb", "max_blocks_per_file", "max_cell_text_length", "processing_order", "plugin_timeout_seconds", "parallel_workers"]},
        {"label": "Rendering/Layout", "fields": ["render_dpi", "render_width_px", "render_height_px", "page_margin_pt", "default_font_size_pt", "code_font_size_pt", "heading_font_size_pt"]},
    ]


def test_read_bundle_returns_same_surface_set_with_values(tmp_path: Path) -> None:
    described = _run_contract(tmp_path, {"action": "describe_surfaces"})
    bundled = _run_contract(tmp_path, {"action": "read_bundle"})

    assert bundled["status"] == "ok"
    assert bundled["module_summary"] == described["module_summary"]
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])


def test_removed_signature_surfaces_fail_closed(tmp_path: Path) -> None:
    payload = _run_contract(
        tmp_path,
        {
            "action": "validate_surface",
            "surface_id": "optimizer.signature_overrides",
            "value": {"version": 1, "overrides": {"file.xlsx": {"unknown_field": "x"}}},
        },
    )
    assert payload["status"] == "error"
    assert "Unbekannte Surface" in payload["reason"]
