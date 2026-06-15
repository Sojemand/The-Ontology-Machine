from __future__ import annotations

from corpus_builder.edit_contract.summary import build_module_summary


def test_build_module_summary_explains_surfaces_actions_and_boundaries() -> None:
    summary = build_module_summary()

    assert summary.startswith("CORPUS BUILDER HELP")
    assert "Search Policy Guide" in summary
    assert "Semantic Release Guide" in summary
    assert "What The Action Buttons Do" in summary
    assert "Recommended First-Time Workflow" in summary
    assert "`hybrid.fts_weight` and `hybrid.vec_weight` split the hybrid score and must add up to `1.0`." in summary
    assert "That workflow belongs to Orchestrator Debug Host or CLI via `scan_debug_input`, `debug_run`, and `load_document`." in summary
