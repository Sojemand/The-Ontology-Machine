from __future__ import annotations

from edit_suite.surfaces.types import ModuleSurfaceBundle


def test_normalizer_bundle_keeps_release_copy_contract_visible(normalizer_bundle: ModuleSurfaceBundle) -> None:
    surfaces = {surface.surface_id: surface for surface in normalizer_bundle.surfaces}

    descriptor = surfaces["normalizer.taxonomy_release_draft"].descriptor
    assert descriptor["source_path"] == "Artifact Tree / Semantic Release/releases/*/release.json"
    assert descriptor["editor_metadata"]["release_search"] == "recursive_release_json"
    assert descriptor["editor_metadata"]["copy_policy"] == "never_mutate_origin"
    assert "edit_projections" in descriptor["editor_metadata"]["tool_catalog"]
    assert "classify_db_update" in descriptor["editor_metadata"]["tool_catalog"]
    assert "Taxonomy / Projection Workflow" in normalizer_bundle.module_summary
    assert "`projection.selection.reason`" in normalizer_bundle.module_summary
