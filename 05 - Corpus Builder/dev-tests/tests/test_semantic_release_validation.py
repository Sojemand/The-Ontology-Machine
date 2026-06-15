from __future__ import annotations

import json

import pytest

from corpus_builder.context import ModuleContext
from corpus_builder.loader.materialization import rematerialized_processing_state
from corpus_builder.semantic_release import (
    load_release_from_path,
    materialize_document_semantics,
    resolve_master_taxonomy_release_id,
    validate_payload_against_release,
)
from corpus_builder.services import load_module_config
from .semantic_release_surface_support import (
    PROJECT_ROOT,
    _refresh_release_fingerprint,
)
from .semantic_release_test_support import build_normalizer_release_bundle, build_release_variant

def test_load_release_from_path_rejects_missing_projection_surface_signals(tmp_path: Path) -> None:
    release_path = tmp_path / "broken.semantic_release.json"
    release = json.loads((PROJECT_ROOT / "config" / "semantic_release.default.json").read_text(encoding="utf-8"))
    release["projections"][0]["routing"].pop("surface_signals", None)
    _refresh_release_fingerprint(release)
    release_path.write_text(json.dumps(release, indent=2, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match=r"projections\[0\]\.routing\.surface_signals"):
        load_release_from_path(release_path)

def test_load_release_from_path_rejects_release_fingerprint_drift(tmp_path: Path) -> None:
    release_path = tmp_path / "drift.semantic_release.json"
    release = json.loads((PROJECT_ROOT / "config" / "semantic_release.default.json").read_text(encoding="utf-8"))
    release["fingerprint"] = "sha256:broken-fingerprint"
    release_path.write_text(json.dumps(release, indent=2, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="fingerprint passt nicht zum Release-Inhalt"):
        load_release_from_path(release_path)

def test_load_release_from_path_rejects_top_level_release_fingerprint_drift(tmp_path: Path) -> None:
    release_path = tmp_path / "alias-drift.semantic_release.json"
    release = json.loads((PROJECT_ROOT / "config" / "semantic_release.default.json").read_text(encoding="utf-8"))
    release["release_fingerprint"] = "sha256:foreign-alias"
    release_path.write_text(json.dumps(release, indent=2, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="release_fingerprint passt nicht zum fingerprint"):
        load_release_from_path(release_path)

def test_load_release_from_path_accepts_legacy_master_taxonomy_release_bridge(tmp_path: Path) -> None:
    release_path = tmp_path / "legacy.semantic_release.json"
    release = json.loads((PROJECT_ROOT / "config" / "semantic_release.default.json").read_text(encoding="utf-8"))
    release.pop("master_taxonomy_release_id", None)
    _refresh_release_fingerprint(release)
    release_path.write_text(json.dumps(release, indent=2, ensure_ascii=False), encoding="utf-8")

    loaded = load_release_from_path(release_path)

    assert "master_taxonomy_release_id" not in loaded
    assert resolve_master_taxonomy_release_id(loaded) == "legacy:normalizer_taxonomy.master@2026-03-28.v6"

def test_validate_payload_against_release_rejects_foreign_master_line(vision_normalized) -> None:
    release = load_release_from_path(PROJECT_ROOT / "config" / "semantic_release.default.json")
    payload = json.loads(json.dumps(vision_normalized))
    payload["projection"]["master_taxonomy_id"] = "foreign.master"

    with pytest.raises(ValueError, match="anderen Master-Taxonomie-Linie"):
        validate_payload_against_release(payload, release)

def test_materialize_document_semantics_promotes_dynamic_slots_and_marks_stale(vision_normalized) -> None:
    release = build_release_variant()
    assert release["projections"][0]["routing"]["surface_signals"]["text_markers"]
    payload = json.loads(json.dumps(vision_normalized))
    payload["projection"]["projection_fingerprint"] = "sha256:outdated"

    result = materialize_document_semantics("semantic_surface_doc", payload, release)

    assert result["document_promotions"]
    assert {promotion["slot"] for promotion in result["document_promotions"]} == {"billing_reference"}
    assert all("query_role" in promotion for promotion in result["document_promotions"])
    assert all(promotion["release_fingerprint"] == release["fingerprint"] for promotion in result["document_promotions"])
    assert any(candidate["strategy"] == "release_promotion" for candidate in result["slot_candidates"])
    assert result["processing_state"]["materialization_state"] == "stale"
    assert result["processing_state"]["stale_reason"] == "projection_fingerprint_mismatch"
    assert any(audit["code"] == "projection_fingerprint_mismatch" for audit in result["audits"])
    persisted_state = rematerialized_processing_state(result, release)
    assert persisted_state["materialization_state"] == "stale"
    assert persisted_state["stale_reason"] == "projection_fingerprint_mismatch"

def test_materialize_document_semantics_promotes_row_wildcard_source_paths(vision_normalized) -> None:
    release = build_release_variant()
    payload = json.loads(json.dumps(vision_normalized))
    slot = {
        "slot": "row_description",
        "label": "Row Description",
        "value_type": "string",
        "scope": "document",
        "cardinality": "multi",
        "query_role": "secondary",
        "display_rank": 99,
    }
    release["master_taxonomy"]["promotion_slots"].append(slot)
    projection_id = str(payload["projection"]["projection_id"])
    projection = next(item for item in release["projections"] if item["projection_id"] == projection_id)
    projection["promotion_rules"] = [
        {"slot": "row_description", "source_paths": ["content.rows[*].description"]}
    ]
    payload["content"]["rows"] = [
        {"description": "First row value"},
        {"description": ""},
        {"description": "Second row value"},
    ]

    result = materialize_document_semantics("row_promotion_doc", payload, release)

    row_promotions = [
        promotion
        for promotion in result["document_promotions"]
        if promotion["slot"] == "row_description"
    ]
    assert [promotion["display_value"] for promotion in row_promotions] == ["First row value", "Second row value"]
    assert {promotion["source_path"] for promotion in row_promotions} == {"content.rows[*].description"}

def test_published_default_release_matches_normalizer_release_identity() -> None:
    context = ModuleContext(PROJECT_ROOT)
    config = load_module_config(context)
    release = load_release_from_path(context.resolve_path(config.semantic.published_release_path))
    expected = build_normalizer_release_bundle(project_root=PROJECT_ROOT)

    assert release["fingerprint"] == expected["fingerprint"]
    assert release["master_taxonomy_release_id"] == expected["master_taxonomy_release_id"]
    assert release["runtime_locale"] == expected["runtime_locale"]
