from __future__ import annotations

from tests.fixtures.taxonomy_refactor_baseline import load_cleanup_manifest


def test_cleanup_manifest_documents_deferred_step1_candidates() -> None:
    manifest = load_cleanup_manifest()

    assert manifest
    for entry in manifest:
        assert entry["candidate_kind"]
        assert entry["reference"]
        assert entry["decision"]
        assert entry["rationale"]
        assert entry["scheduled_step"]


def test_cleanup_manifest_covers_known_step1_split_and_legacy_candidates() -> None:
    references = {entry["reference"] for entry in load_cleanup_manifest()}

    assert any("projection_templates" in reference for reference in references)
    assert any("routing.when_to_use" in reference for reference in references)
    assert any("routing.avoid_when" in reference for reference in references)
    assert any("surface_signals.text_markers" in reference for reference in references)
    assert any("legacy_owner" in reference for reference in references)
