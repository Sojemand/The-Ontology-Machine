from __future__ import annotations

import json

from corpus_builder.database import CORPUS_SCHEMA_VERSION
from tests.fixtures.loader_io import load_input_file
from .semantic_release_test_support import build_release_variant

def test_load_from_file_vision_happy_path(db, vision_structured, vision_normalized, vision_validation_report, make_input_pair):
    raw_payload = {
        "doc": {"file_name": "vision_invoice.pdf"},
        "ctx": {"document_date": "2023-06-27", "total_amount": 318.79},
        "guardrail": {"sections": [{"id": "source_p01_c00", "text": "Zu zahlender Betrag 318,79 EUR"}]},
    }
    json_path = make_input_pair(
        "vision_invoice",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
        raw=raw_payload,
    )

    result = load_input_file(db, json_path, semantic_release=build_release_variant())

    assert result.status == "loaded"
    row = db.execute(
        "SELECT validator_status, needs_review, interpreter_needs_review, interpreter_review_reason, normalizer_needs_review, validator_issues_count, content_fields_json, content_rows_json "
        "FROM documents WHERE id = ?",
        ("vision_invoice",),
    ).fetchone()
    assert row["validator_status"] == "pass"
    assert row["needs_review"] == 1
    assert row["interpreter_needs_review"] == 1
    assert row["interpreter_review_reason"] == "Legacy OCR refs did not fully confirm values."
    assert row["normalizer_needs_review"] == 0
    assert row["validator_issues_count"] == 0

    fields_json = json.loads(row["content_fields_json"])
    rows_json = json.loads(row["content_rows_json"])
    assert "_source_refs" not in fields_json
    assert "_source_refs" not in rows_json[0]
    assert rows_json[0]["_row_type"] == "line_item"
    assert rows_json[0]["_row_index"] == 0
    assert fields_json["reference_number"] == "ENV 100002966355"
    assert fields_json["invoice_number"] == "ENV 100002966355"
    assert fields_json["currency"] == "EUR"
    assert rows_json[0]["position"] == "zu zahlender betrag"

    payload = db.execute(
        "SELECT schema_version, corpus_schema_version, structured_json, raw_json, normalized_json, projection_json, free_text FROM document_payloads WHERE document_id = ?",
        ("vision_invoice",),
    ).fetchone()
    assert payload["schema_version"] == "1.1"
    assert payload["corpus_schema_version"] == CORPUS_SCHEMA_VERSION
    assert json.loads(payload["structured_json"])["projection"]["slots"][0]["slot"] == "document_type"
    assert json.loads(payload["raw_json"])["ctx"]["total_amount"] == 318.79
    assert json.loads(payload["normalized_json"])["content"]["fields"]["reference_number"] == "ENV 100002966355"
    assert json.loads(payload["projection_json"])["projection_id"] == "housing.default.v1"
    assert "Zu zahlender Betrag" in payload["free_text"]
    assert "Faellig am 11.07.2023" not in payload["free_text"]

    atom = db.execute(
        "SELECT atom_type, source_ref, text_value, normalized_text, row_index, column_key, anchor_kind, anchor_key FROM evidence_atoms WHERE document_id = ? AND json_path = ?",
        ("vision_invoice", "content.rows[0].brutto"),
    ).fetchone()
    assert atom["atom_type"] == "row_cell"
    assert atom["source_ref"] == "page1_para_55"
    assert atom["text_value"] == "318.79"
    assert atom["normalized_text"] == "318 79"
    assert atom["row_index"] == 0
    assert atom["column_key"] == "brutto"
    assert atom["anchor_kind"] == "row"
    assert atom["anchor_key"] == "row:0"

    candidate = db.execute(
        "SELECT slot, display_value, strategy, is_projection_backed, candidate_layer, candidate_origin, origin_path FROM slot_candidates WHERE document_id = ? AND slot = ? ORDER BY is_projection_backed DESC, candidate_id ASC",
        ("vision_invoice", "billing_reference"),
    ).fetchone()
    assert candidate["display_value"] == "ENV 100002966355"
    assert candidate["strategy"] == "release_promotion"
    assert candidate["is_projection_backed"] == 1
    assert candidate["candidate_layer"] == "release"
    assert candidate["candidate_origin"] == "release_promotion"
    assert candidate["origin_path"] == "content.fields.reference_number"
    promotion = db.execute(
        "SELECT slot, display_value, query_role, candidate_id, source_path, is_current FROM document_promotions WHERE document_id = ? AND slot = ?",
        ("vision_invoice", "billing_reference"),
    ).fetchone()
    assert promotion["display_value"] == "ENV 100002966355"
    assert promotion["query_role"] == "identifier"
    assert promotion["candidate_id"] is not None
    assert promotion["source_path"] == "content.fields.reference_number"
    assert promotion["is_current"] == 1
    assert db.execute(
        "SELECT COUNT(*) FROM vw_document_promotions_current WHERE document_id = ? AND slot = ?",
        ("vision_invoice", "billing_reference"),
    ).fetchone()[0] == 1
