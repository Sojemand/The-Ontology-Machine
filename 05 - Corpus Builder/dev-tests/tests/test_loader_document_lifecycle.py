"""Loader archive, duplicate, and reload lifecycle tests."""

from __future__ import annotations

import json

from corpus_builder.loader import rematerialize_document
from tests.semantic_release_test_support import build_release_variant
from tests.fixtures.loader_io import load_input_file


def test_archive_on_new_hash_same_file(db, vision_structured, vision_validation_report, make_input_pair):
    first = dict(vision_structured)
    first["source"] = dict(vision_structured["source"])
    first["source"]["content_hash"] = "sha256:first"
    second = dict(vision_structured)
    second["source"] = dict(vision_structured["source"])
    second["source"]["content_hash"] = "sha256:second"

    assert load_input_file(db, make_input_pair("doc_a", first, vision_report=vision_validation_report)).status == "loaded"
    assert load_input_file(db, make_input_pair("doc_b", second, vision_report=vision_validation_report)).status == "archived_and_loaded"

    rows = db.execute("SELECT id, is_archived, superseded_by FROM documents ORDER BY id").fetchall()
    assert rows[0]["id"] == "doc_a"
    assert rows[0]["is_archived"] == 1
    assert rows[0]["superseded_by"] == "doc_b"
    assert rows[1]["is_archived"] == 0


def test_same_hash_different_id_same_file_is_skipped_as_duplicate(db, vision_structured, vision_validation_report, make_input_pair):
    path_one = make_input_pair("scan_p01", dict(vision_structured), vision_report=vision_validation_report)
    path_two = make_input_pair("scan_p02", dict(vision_structured), vision_report=vision_validation_report)

    assert load_input_file(db, path_one).status == "loaded"
    result = load_input_file(db, path_two)

    assert result.status == "skipped"
    assert result.reason == "duplicate_file_path"
    assert db.execute("SELECT COUNT(*) FROM documents WHERE is_archived = 0").fetchone()[0] == 1


def test_same_document_id_different_file_path_returns_collision_error(db, vision_structured, vision_validation_report, tmp_path):
    first_dir = tmp_path / "one"
    second_dir = tmp_path / "two"
    first_dir.mkdir()
    second_dir.mkdir()
    first = dict(vision_structured)
    second = dict(vision_structured)
    second["source"] = dict(vision_structured["source"])
    second["source"]["file_path"] = "C:/docs/other-source.pdf"
    first_path = first_dir / "same.structured.json"
    second_path = second_dir / "same.structured.json"
    first_path.write_text(json.dumps(first, indent=2, ensure_ascii=False), encoding="utf-8")
    second_path.write_text(json.dumps(second, indent=2, ensure_ascii=False), encoding="utf-8")
    (first_dir / "same.vision_validation_report.json").write_text(json.dumps(vision_validation_report, indent=2, ensure_ascii=False), encoding="utf-8")
    (second_dir / "same.vision_validation_report.json").write_text(json.dumps(vision_validation_report, indent=2, ensure_ascii=False), encoding="utf-8")

    assert load_input_file(db, first_path).status == "loaded"
    result = load_input_file(db, second_path)

    assert result.status == "error"
    assert "document_id collision" in result.reason
    row = db.execute("SELECT file_path FROM documents WHERE id = ?", ("same",)).fetchone()
    assert row["file_path"] == "C:/docs/2026-03-13 17-33.pdf"


def test_same_id_same_path_same_hash_is_skipped_without_new_rows(db, vision_structured, vision_validation_report, make_input_pair):
    json_path = make_input_pair("stable_doc", vision_structured, vision_report=vision_validation_report)
    assert load_input_file(db, json_path).status == "loaded"
    before_history = db.execute("SELECT COUNT(*) FROM load_history").fetchone()[0]

    result = load_input_file(db, json_path)

    assert result.status == "skipped"
    assert result.reason == "identical"
    assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM load_history").fetchone()[0] == before_history


def test_same_document_id_new_hash_reloads_in_place(
    db,
    vision_structured,
    vision_validation_report,
    vision_normalized,
    make_input_pair,
):
    first = dict(vision_structured)
    first["source"] = dict(vision_structured["source"])
    first["source"]["content_hash"] = "sha256:first-version"
    second = dict(first)
    second["source"] = dict(first["source"])
    second["source"]["content_hash"] = "sha256:second-version"
    second["content"] = dict(vision_structured["content"])
    second["content"]["fields"] = dict(vision_structured["content"]["fields"])
    second["content"]["fields"]["invoice_number"] = "UPDATED-42"
    second_normalized = dict(vision_normalized)
    second_normalized["content"] = dict(vision_normalized["content"])
    second_normalized["content"]["fields"] = dict(vision_normalized["content"]["fields"])
    second_normalized["content"]["fields"]["invoice_number"] = "UPDATED-42"
    second_normalized["source"] = dict(vision_normalized.get("source") or {})
    second_normalized["source"]["content_hash"] = "sha256:second-version"
    json_path = make_input_pair("mutable_doc", first, vision_report=vision_validation_report)

    assert load_input_file(db, json_path).status == "loaded"
    json_path.write_text(json.dumps(second, indent=2, ensure_ascii=False), encoding="utf-8")
    json_path.with_name("mutable_doc.structured.normalized.json").write_text(
        json.dumps(second_normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    result = load_input_file(db, json_path)

    assert result.status == "archived_and_loaded"
    row = db.execute("SELECT content_hash FROM documents WHERE id = ?", ("mutable_doc",)).fetchone()
    field = db.execute("SELECT value FROM extracted_fields WHERE document_id = ? AND key = ?", ("mutable_doc", "invoice_number")).fetchone()
    assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert row["content_hash"] == "sha256:second-version"
    assert field["value"] == "UPDATED-42"


def test_rematerialize_preserves_observed_segments(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
) -> None:
    release = build_release_variant()
    release_projection = next(
        item for item in release["projections"] if item["projection_id"] == vision_normalized["projection"]["projection_id"]
    )
    normalized = json.loads(json.dumps(vision_normalized))
    normalized["projection"]["master_taxonomy_id"] = release["master_taxonomy_id"]
    normalized["projection"]["master_taxonomy_version"] = release["master_taxonomy_version"]
    normalized["projection"]["projection_fingerprint"] = release_projection["projection_fingerprint"]
    structured = dict(vision_structured)
    structured["content"] = dict(vision_structured["content"])
    structured["content"]["segments"] = [
        {
            "segment_id": "seg_001",
            "unit_kind": "question",
            "page": 1,
            "sequence": 1,
            "text": "Kann die Anlage betrieben werden?",
            "_source_refs": {"text": ["page1_para_1"]},
        }
    ]
    json_path = make_input_pair("remat_doc", structured, vision_report=vision_validation_report, normalized=normalized)

    assert load_input_file(db, json_path).status == "loaded"
    assert rematerialize_document(db, "remat_doc", release).status == "loaded"

    observed = db.execute(
        "SELECT COUNT(*) FROM document_entities WHERE document_id = ? AND state = 'observed' AND entity_type = 'segment'",
        ("remat_doc",),
    ).fetchone()[0]
    materialized = db.execute(
        "SELECT COUNT(*) FROM document_entities WHERE document_id = ? AND state = 'materialized'",
        ("remat_doc",),
    ).fetchone()[0]
    state = db.execute(
        "SELECT materialization_state, projection_id FROM document_processing_state WHERE document_id = ?",
        ("remat_doc",),
    ).fetchone()

    assert observed == 1
    assert materialized >= 0
    assert state["materialization_state"] == "current"
