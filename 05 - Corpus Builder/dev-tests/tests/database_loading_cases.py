from __future__ import annotations

import json

import pytest

from corpus_builder.database import count, get_fields_dict, get_rows_list, group_count

from .database_test_support import load_from_file


def test_helpers_return_expected_fields_and_rows(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    json_path = make_input_pair(
        "helper_doc",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )
    assert load_from_file(db, json_path).status == "loaded"

    fields = get_fields_dict(db, "helper_doc")
    rows = get_rows_list(db, "helper_doc")
    assert fields["reference_number"] == "ENV 100002966355"
    assert fields["invoice_number"] == "ENV 100002966355"
    assert fields["amount_due"] == 318.79
    assert fields["currency"] == "EUR"
    assert rows[0]["position"] == "zu zahlender betrag"


def test_content_json_preserves_non_internal_values(
    db,
    mixed_structured,
    legacy_validation_report,
    make_input_pair,
):
    json_path = make_input_pair("content_json_doc", mixed_structured, legacy_report=legacy_validation_report)
    assert load_from_file(db, json_path).status == "loaded"

    row = db.execute(
        "SELECT content_fields_json, content_rows_json FROM documents WHERE id = ?",
        ("content_json_doc",),
    ).fetchone()
    fields_json = json.loads(row["content_fields_json"])
    rows_json = json.loads(row["content_rows_json"])
    assert fields_json["invoice_number"] == "BUD-2024-01"
    assert rows_json[0]["category"] == "Wasser"


def test_query_helpers_reject_unknown_identifiers(db):
    with pytest.raises(ValueError, match="Unerlaubter Bezeichner"):
        count(db, "unknown_table")

    with pytest.raises(ValueError, match="Unerlaubter Bezeichner"):
        group_count(db, "documents", "unknown_column")


def test_extracted_fields_store_search_variants(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    json_path = make_input_pair(
        "search_doc",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )
    assert load_from_file(db, json_path).status == "loaded"

    row = db.execute(
        "SELECT normalized_value, compact_value FROM extracted_fields WHERE document_id = ? AND key = ?",
        ("search_doc", "reference_number"),
    ).fetchone()
    assert row["normalized_value"] == "env 100002966355"
    assert row["compact_value"] == "env100002966355"

    legacy_row = db.execute(
        "SELECT normalized_value, compact_value FROM extracted_fields WHERE document_id = ? AND key = ?",
        ("search_doc", "invoice_number"),
    ).fetchone()
    assert legacy_row["normalized_value"] == "env 100002966355"
    assert legacy_row["compact_value"] == "env100002966355"


def test_extracted_fields_flatten_scalar_list_values(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    normalized = json.loads(json.dumps(vision_normalized))
    normalized["content"]["fields"]["theme"] = ["family dynamics", "revenge"]
    normalized["content"]["fields"]["ignored_objects"] = [{"label": "not scalar"}]

    json_path = make_input_pair(
        "multi_field_doc",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=normalized,
    )
    assert load_from_file(db, json_path).status == "loaded"

    rows = db.execute(
        "SELECT key, value, normalized_value, compact_value FROM extracted_fields WHERE document_id = ? AND key = ? ORDER BY id",
        ("multi_field_doc", "theme"),
    ).fetchall()
    assert [row["value"] for row in rows] == ["family dynamics", "revenge"]
    assert [row["normalized_value"] for row in rows] == ["family dynamics", "revenge"]
    assert [row["compact_value"] for row in rows] == ["familydynamics", "revenge"]
    assert db.execute(
        "SELECT COUNT(*) FROM extracted_fields WHERE document_id = ? AND key = ?",
        ("multi_field_doc", "ignored_objects"),
    ).fetchone()[0] == 0
