from __future__ import annotations

import json
from pathlib import Path

import pytest

from normalizer_vision.semantic_release import (
    analyze_taxonomy_shape,
    build_semantic_release,
    default_publish_output_path,
    load_local_projection_payloads,
    load_recipe,
    publish_semantic_release,
    semantic_release_file_name,
    validate_recipe_payload,
)
from tests.fixtures.taxonomy_source_package import package_paths, read_yaml, write_yaml


def test_build_semantic_release_includes_master_and_projection_metadata(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root, release_id="test.release")

    assert release["release_id"] == "test.release"
    assert release["release_version"]
    assert release["materialization_version"]
    assert release["fingerprint"].startswith("sha256:")
    assert release["master_taxonomy"]["entity_types"]
    assert release["projections"]
    assert release["projections"][0]["projection_family"]
    assert "promotion_rules" in release["projections"][0]
    assert release["projections"][0]["routing"]["surface_signals"]["text_markers"]
    assert release["projection_catalog"]["release_id"] == "test.release"
    assert release["projection_catalog"]["release_fingerprint"] == release["fingerprint"]
    assert release["runtime_semantic_assets"]["release_id"] == "test.release"
    assert release["runtime_semantic_assets"]["projection_catalog"] == release["projection_catalog"]


def test_build_semantic_release_preserves_recipe_projection_order(tmp_project_root: Path):
    recipe = load_recipe(tmp_project_root)
    release = build_semantic_release(tmp_project_root)

    assert release["projection_ids"] == recipe["projection_ids"]
    assert [projection["projection_id"] for projection in release["projections"]] == recipe["projection_ids"]


def test_build_semantic_release_rejects_missing_surface_signals(tmp_project_root: Path):
    projection = package_paths(tmp_project_root).projections[2]
    payload = read_yaml(projection.core_path)
    payload["routing"]["section_roles"] = []
    payload["routing"]["party_roles"] = []
    write_yaml(projection.core_path, payload)
    text_payload = read_yaml(projection.text_path)
    text_payload["routing_lexicon"]["text_markers"] = []
    text_payload["routing_lexicon"]["domain_markers"] = {}
    write_yaml(projection.text_path, text_payload)

    with pytest.raises(ValueError, match="routing_lexicon|surface_signals"):
        build_semantic_release(tmp_project_root)


def test_publish_semantic_release_writes_json_file(tmp_project_root: Path):
    output_path = default_publish_output_path(
        tmp_project_root,
        "semantic_release.default",
        release_version="2026-03-28.v6",
        runtime_locale="en",
    )
    release = publish_semantic_release(tmp_project_root)

    assert output_path.exists()
    assert release["release_id"] == "semantic_release.default"
    assert release["runtime_locale"] == "en"
    stored_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert stored_payload["projection_catalog"]["release_fingerprint"] == release["fingerprint"]
    assert stored_payload["runtime_semantic_assets"]["release_fingerprint"] == release["fingerprint"]
    assert stored_payload["runtime_semantic_assets"]["projection_catalog"] == stored_payload["projection_catalog"]


def test_publish_semantic_release_accepts_explicit_output_path(tmp_project_root: Path):
    output_path = tmp_project_root / "output" / "semantic_release.custom.json"
    release = publish_semantic_release(tmp_project_root, output_path)

    assert release["release_id"] == "semantic_release.default"
    assert output_path.exists()


def test_load_recipe_reads_bootstrapped_file(tmp_project_root: Path):
    recipe = load_recipe(tmp_project_root)

    assert recipe["release_id"] == "semantic_release.default"
    assert recipe["release_version"] == "2026-03-28.v6"
    assert "operations.default.v1" in recipe["projection_ids"]


def test_load_recipe_rejects_drift_from_source_release(tmp_project_root: Path):
    recipe_path = tmp_project_root / "config" / "semantic_release.recipe.json"
    payload = json.loads(recipe_path.read_text(encoding="utf-8"))
    payload["release_version"] = "drifted"
    recipe_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="driftet vom Source-Paket ab"):
        load_recipe(tmp_project_root)


def test_validate_recipe_payload_rejects_missing_projection(tmp_project_root: Path):
    with pytest.raises(ValueError, match="Lokale Projection nicht gefunden: missing.projection"):
        validate_recipe_payload(
            tmp_project_root,
            {
                "release_id": "semantic_release.default",
                "release_version": "1",
                "projection_ids": ["housing.default.v1", "missing.projection"],
                "materialization_version": "1",
            },
        )


def test_validate_recipe_payload_rejects_missing_materialization_version(tmp_project_root: Path):
    with pytest.raises(ValueError, match="fehlende Felder: materialization_version"):
        validate_recipe_payload(
            tmp_project_root,
            {
                "release_id": "semantic_release.default",
                "release_version": "1",
                "projection_ids": ["housing.default.v1"],
            },
        )


def test_validate_recipe_payload_rejects_blank_materialization_version(tmp_project_root: Path):
    with pytest.raises(ValueError, match="materialization_version"):
        validate_recipe_payload(
            tmp_project_root,
            {
                "release_id": "semantic_release.default",
                "release_version": "1",
                "projection_ids": ["housing.default.v1"],
                "materialization_version": " ",
            },
        )


def test_analyze_taxonomy_shape_reports_projection_gap(tmp_project_root: Path):
    release = build_semantic_release(tmp_project_root)
    report = analyze_taxonomy_shape(release["master_taxonomy"], release["projections"])

    assert report["summary"]["projection_count"] >= 1
    assert "issues" in report
    assert "warnings" in report


def test_release_fingerprint_is_stable_for_identical_semantics(tmp_project_root: Path):
    first = build_semantic_release(tmp_project_root, release_id="stable.release")
    second = build_semantic_release(tmp_project_root, release_id="stable.release")

    assert first["created_at"]
    assert second["created_at"]
    assert first["fingerprint"] == second["fingerprint"]


def test_build_semantic_release_materializes_requested_runtime_locale(tmp_project_root: Path):
    default_release = build_semantic_release(tmp_project_root)
    explicit_release = build_semantic_release(tmp_project_root, target_locale="en")

    assert default_release["runtime_locale"] == "en"
    assert explicit_release["runtime_locale"] == "en"
    assert explicit_release["master_taxonomy_release_id"] == default_release["master_taxonomy_release_id"]
    assert explicit_release["master_taxonomy_release_id"].startswith("sha256:")


def test_publish_semantic_release_stamps_default_file_name_with_locale(tmp_project_root: Path):
    release = publish_semantic_release(tmp_project_root, target_locale="en")
    output_path = default_publish_output_path(
        tmp_project_root,
        release["release_id"],
        release_version=release["release_version"],
        runtime_locale=release["runtime_locale"],
    )

    assert output_path.exists()
    assert output_path.name == "semantic_release.default__2026-03-28.v6__en.json"


def test_semantic_release_file_name_sanitizes_release_id():
    assert semantic_release_file_name(" stable/release name ") == "stable.release_name.json"


def test_load_local_projection_payloads_rejects_missing_selected_projection(tmp_project_root: Path):
    with pytest.raises(ValueError, match="Lokale Projection nicht gefunden: missing.projection"):
        load_local_projection_payloads(tmp_project_root, ["housing.default.v1", "missing.projection"])


def test_load_local_projection_payloads_preserve_requested_order(tmp_project_root: Path):
    selected_projection_ids = ["housing.default.v1", "finance.default.v1", "community.spiritual.default.v1"]

    payloads = load_local_projection_payloads(tmp_project_root, selected_projection_ids)

    assert [payload["projection_id"] for payload in payloads] == selected_projection_ids
