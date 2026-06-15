from __future__ import annotations

import json

import pytest

from normalizer_vision.assets import (
    build_projection_catalog,
    find_local_profile_spec,
    list_local_profiles,
    load_local_profile,
    prompt_bundle_path,
    prompt_overrides_path,
    semantic_release_recipe_path,
)
from normalizer_vision.taxonomy_compile import ensure_compiled_taxonomy_assets

CORE_PROJECTION_IDS = [
    "business.customer.communication.default.v1",
    "community.spiritual.default.v1",
    "finance.default.v1",
    "health.care.default.v1",
    "housing.default.v1",
    "legal.public_admin.default.v1",
    "operations.default.v1",
    "people.identity.default.v1",
    "personal.expression.default.v1",
    "personal.wellbeing.default.v1",
    "technical.default.v1",
]


def test_asset_paths_point_to_local_config_files(tmp_project_root):
    assert prompt_bundle_path(tmp_project_root) == tmp_project_root / "config" / "prompt_bundle.json"
    assert prompt_overrides_path(tmp_project_root) == tmp_project_root / "config" / "prompt_overrides.json"
    assert semantic_release_recipe_path(tmp_project_root) == tmp_project_root / "config" / "semantic_release.recipe.json"


def test_list_local_profiles_ignore_shadow_projection_files(tmp_project_root):
    config_dir = tmp_project_root / "config"
    (config_dir / "normalizer_taxonomy.broken.json").write_text("{broken", encoding="utf-8")
    (config_dir / "normalizer_taxonomy.empty.json").write_text("[]", encoding="utf-8")
    (config_dir / "normalizer_taxonomy.no_projection.json").write_text(json.dumps({"label": "No ID"}), encoding="utf-8")

    profiles = list_local_profiles(tmp_project_root)

    assert [profile.projection_id for profile in profiles] == CORE_PROJECTION_IDS


def test_list_local_profiles_preserve_release_order(tmp_project_root):
    profiles = list_local_profiles(tmp_project_root)

    assert [profile.projection_id for profile in profiles] == CORE_PROJECTION_IDS


def test_find_local_profile_spec_returns_none_for_unknown_profile(tmp_project_root):
    assert find_local_profile_spec(tmp_project_root, "missing.profile") is None


def test_load_local_profile_rejects_empty_profile_id(tmp_project_root):
    with pytest.raises(ValueError, match="taxonomy_profile_id darf nicht leer sein"):
        load_local_profile(tmp_project_root, " ")


def test_load_local_profile_rejects_missing_profile(tmp_project_root):
    with pytest.raises(ValueError, match="Lokales Taxonomie-Profil nicht gefunden"):
        load_local_profile(tmp_project_root, "missing.profile")


def test_build_projection_catalog_preserves_release_order(tmp_project_root):
    catalog = build_projection_catalog(tmp_project_root)
    entries_by_id = {entry.projection_id: entry for entry in catalog.projections}

    assert catalog.master_taxonomy_version == "2026-03-28.v6"
    assert catalog.catalog_version.startswith("sha256:")
    assert [entry.projection_id for entry in catalog.projections] == CORE_PROJECTION_IDS
    assert entries_by_id["operations.default.v1"].when_to_use.startswith("Logistics, procurement, technical execution")
    assert all(entry.when_to_use and entry.avoid_when and entry.example_document_types for entry in catalog.projections)


def test_all_projection_files_define_complete_routing_blocks(tmp_project_root):
    compiled = ensure_compiled_taxonomy_assets(tmp_project_root)
    assert compiled is not None
    for projection_id, payload in sorted(compiled.projections.items()):
        routing = payload.get("routing")
        assert isinstance(routing, dict), projection_id
        assert routing.get("when_to_use"), projection_id
        assert routing.get("avoid_when"), projection_id
        assert isinstance(routing.get("example_document_types"), list) and routing["example_document_types"], projection_id
