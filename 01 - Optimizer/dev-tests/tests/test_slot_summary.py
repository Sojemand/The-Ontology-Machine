from __future__ import annotations

from ingestion_layer_vision.edit_contract.summary import build_module_summary


def test_build_module_summary_describes_settings_and_minimal_vision_contract() -> None:
    summary = build_module_summary()

    assert summary.startswith("OPTIMIZER HELP")
    assert "Surface Guide" in summary
    assert "Settings (`optimizer.settings`)" in summary
    assert "LLM-OCR Prompt (`optimizer.ocr_prompt`)" in summary
    assert "Output Contract Preview (`optimizer.output_contract_preview`)" in summary
    assert "Debug Capabilities (`optimizer.debug_capabilities`)" in summary
    assert "`optimizer_raw_v2`" in summary
    assert "`ocr_reference.blocks`" in summary
    assert "`optimizer_ocr` LLM target" in summary
    assert "`OPTIMIZER_OCR_*` process overlay" in summary
    assert "`render_dpi`" in summary
    assert "`{page_count}`" in summary
    assert "summaries, sections, facts, tables" in summary
    assert "It does not author projection catalogs or semantic extraction policy." in summary
