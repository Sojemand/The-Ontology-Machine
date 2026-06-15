from __future__ import annotations

from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces.sections import build_sections
from edit_suite.surfaces.types import ModuleSurfaceBundle


def test_normalizer_bundle_exposes_single_taxonomy_release_draft_surface(
    normalizer_entry: ModuleReadinessEntry,
    normalizer_bundle: ModuleSurfaceBundle,
) -> None:
    sections = {section.name: section for section in build_sections(normalizer_entry, normalizer_bundle, {})}
    surfaces = {surface.surface_id: surface for surface in normalizer_bundle.surfaces}

    assert "Taxonomy / Projection Workflow" in sections["Summary"].body
    assert "config/taxonomy_sources" not in sections["Summary"].body
    assert "Create Projection Draft" not in sections["Summary"].body
    assert surfaces["normalizer.taxonomy_release_draft"].editor_kind == "taxonomy_release_draft"
    assert surfaces["normalizer.taxonomy_release_draft"].descriptor["validate_label"] == "Verify"
    assert surfaces["normalizer.taxonomy_release_draft"].descriptor["save_label"] == "Write Copy"
    assert surfaces["normalizer.taxonomy_release_draft"].descriptor["editor_metadata"]["copy_policy"] == "never_mutate_origin"
    assert [surface.surface_id for surface in sections["Prompts/Assets"].surfaces] == [
        "normalizer.prompt_overrides",
        "normalizer.prompt_bundle",
        "normalizer.taxonomy_release_draft",
    ]
    assert "normalizer.taxonomy_master" not in surfaces
    assert "normalizer.taxonomy_profiles" not in surfaces
    assert "normalizer.semantic_release_authoring" not in surfaces
