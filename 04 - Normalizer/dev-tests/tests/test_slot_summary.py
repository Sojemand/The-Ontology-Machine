from __future__ import annotations

from normalizer_vision.edit_contract.summary import build_module_summary


def test_build_module_summary_describes_taxonomy_management_and_release_flow() -> None:
    summary = build_module_summary()

    assert summary.startswith("NORMALIZER HELP")
    assert "Taxonomy / Projection Workflow" in summary
    assert "normalizer.taxonomy_release_draft" in summary
    assert "Artifact Tree" in summary
    assert "Semantic Release/drafts/edit_suite/<release_id>/release.json" in summary
    assert "routing.surface_signals" in summary
    assert "`Verify`" in summary
    assert "`Write Copy`" in summary
    assert "update_current_db_with_auto_refill" in summary
    assert "materialize_new_db" in summary
    assert "config/taxonomy_sources/<release_id>/" not in summary
