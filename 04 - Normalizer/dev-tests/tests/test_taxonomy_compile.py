from __future__ import annotations

import json

import pytest

from normalizer_vision.assets import list_local_profiles
from normalizer_vision.runtime_semantic_assets import build_runtime_semantic_assets
from normalizer_vision.semantic_release import build_semantic_release
from normalizer_vision.taxonomy_compile import ensure_compiled_taxonomy_assets
from normalizer_vision.taxonomy_sources.governance import sync_release_governance
from tests.fixtures.taxonomy_source_package import clone_locale, package_paths, read_yaml, write_yaml
from tests.fixtures.taxonomy_refactor_baseline import (
    INVENTORY_CASES,
    MASTER_SNAPSHOT_NAME,
    PROJECTION_SNAPSHOT_NAMES,
    RELEASE_SNAPSHOT_NAME,
    RUNTIME_SNAPSHOT_NAME,
    comparable_snapshot_fingerprint,
    core_leaf_values,
    load_fingerprint_manifest,
    load_snapshot_payload,
    normalize_release_payload,
)

COMPILED_SNAPSHOT_NAMES = (MASTER_SNAPSHOT_NAME, *PROJECTION_SNAPSHOT_NAMES)


def test_compiled_taxonomy_payloads_match_baseline_snapshots(tmp_project_root):
    compiled = ensure_compiled_taxonomy_assets(tmp_project_root)
    assert compiled is not None
    case_lookup = {
        snapshot_name: (artifact_kind, projection_id)
        for artifact_kind, snapshot_name, projection_id in INVENTORY_CASES
    }

    for snapshot_name in COMPILED_SNAPSHOT_NAMES:
        artifact_kind, projection_id = case_lookup[snapshot_name]
        observed = (
            compiled.master
            if projection_id is None
            else compiled.projections[projection_id]
        )
        artifact_kind, projection_id = case_lookup[snapshot_name]
        assert core_leaf_values(
            observed,
            artifact_kind=artifact_kind,
            projection_id=projection_id,
        ) == core_leaf_values(
            load_snapshot_payload(snapshot_name),
            artifact_kind=artifact_kind,
            projection_id=projection_id,
        )


def test_compiled_taxonomy_payload_fingerprints_match_baseline_manifest(tmp_project_root):
    compiled = ensure_compiled_taxonomy_assets(tmp_project_root)
    assert compiled is not None
    manifest = load_fingerprint_manifest()
    case_lookup = {
        snapshot_name: (artifact_kind, projection_id)
        for artifact_kind, snapshot_name, projection_id in INVENTORY_CASES
    }
    observed = {
        snapshot_name: comparable_snapshot_fingerprint(
            compiled.master if case_lookup[snapshot_name][1] is None else compiled.projections[case_lookup[snapshot_name][1]],
            artifact_kind=case_lookup[snapshot_name][0],
            projection_id=case_lookup[snapshot_name][1],
        )
        for snapshot_name in COMPILED_SNAPSHOT_NAMES
    }

    assert observed == {snapshot_name: manifest[snapshot_name] for snapshot_name in COMPILED_SNAPSHOT_NAMES}


def test_compiled_release_and_runtime_assets_match_baseline(tmp_project_root):
    ensure_compiled_taxonomy_assets(tmp_project_root)
    release = build_semantic_release(tmp_project_root)
    runtime_assets = build_runtime_semantic_assets(release).to_dict()

    assert core_leaf_values(
        normalize_release_payload(release),
        artifact_kind="semantic_release",
    ) == core_leaf_values(
        load_snapshot_payload(RELEASE_SNAPSHOT_NAME),
        artifact_kind="semantic_release",
    )
    assert core_leaf_values(
        runtime_assets,
        artifact_kind="runtime_semantic_assets",
    ) == core_leaf_values(
        load_snapshot_payload(RUNTIME_SNAPSHOT_NAME),
        artifact_kind="runtime_semantic_assets",
    )


def test_source_changes_do_not_materialize_legacy_compatibility_files(tmp_project_root):
    paths = package_paths(tmp_project_root)
    master_text = read_yaml(paths.master_text_path)
    master_text["description"] = "Aktualisierte deutsche Beschreibung ohne automatisches Compile."
    write_yaml(paths.master_text_path, master_text)

    profiles = list_local_profiles(tmp_project_root)

    assert profiles
    assert not any((tmp_project_root / "config").glob("normalizer_taxonomy.*.json"))


def test_compile_ignores_stale_projection_files_left_by_test_fixtures(tmp_project_root):
    paths = package_paths(tmp_project_root)
    removed_projection = paths.projections[-1]
    stale_path = tmp_project_root / "config" / f"normalizer_taxonomy.{removed_projection.projection_id}.json"
    stale_path.write_text("{}", encoding="utf-8")
    release = read_yaml(paths.release_path)
    release["projection_ids"] = [projection_id for projection_id in release["projection_ids"] if projection_id != removed_projection.projection_id]
    glossary_locales = sorted(
        path.stem.removeprefix("translation_glossary.")
        for path in paths.root.glob("translation_glossary.*.yaml")
    )
    write_yaml(
        paths.release_path,
        sync_release_governance(release, glossary_locales=glossary_locales),
    )
    removed_projection.core_path.unlink()
    for text_path in removed_projection.texts:
        text_path.text_path.unlink()

    compiled = ensure_compiled_taxonomy_assets(tmp_project_root)
    assert compiled is not None

    assert stale_path.exists()
    assert removed_projection.projection_id not in compiled.projections


def test_compiled_master_projection_templates_follow_release_order(tmp_project_root):
    compiled = ensure_compiled_taxonomy_assets(tmp_project_root)
    assert compiled is not None
    release = read_yaml(package_paths(tmp_project_root).release_path)
    assert [template["projection_id"] for template in compiled.master["projection_templates"]] == release["projection_ids"]


def test_compile_bridge_rejects_non_en_extra_locale(tmp_project_root):
    baseline_compiled = ensure_compiled_taxonomy_assets(tmp_project_root)
    assert baseline_compiled is not None

    with pytest.raises(ValueError, match="en-only"):
        clone_locale(tmp_project_root, target_locale="fr")
