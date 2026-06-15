from __future__ import annotations

from .search_surface_support import load_from_file
from .semantic_release_test_support import build_release_variant
from corpus_builder.search import fulltext_search


def test_fulltext_search_hits_free_text(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
):
    json_path = make_input_pair("fts_invoice", vision_structured, vision_report=vision_validation_report)
    assert load_from_file(db, json_path).status == "loaded"

    results = fulltext_search(db, "Schlussrechnung", limit=5)
    assert results
    assert results[0].document_id == "fts_invoice"


def test_fulltext_search_hits_metadata_columns(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    json_path = make_input_pair(
        "fts_meta",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )
    assert load_from_file(db, json_path).status == "loaded"

    results = fulltext_search(db, "Lastschrift", limit=5)
    assert results
    assert results[0].document_id == "fts_meta"


def test_fulltext_search_indexes_dynamic_document_promotions(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    json_path = make_input_pair(
        "fts_promotion",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )
    assert load_from_file(db, json_path, semantic_release=build_release_variant()).status == "loaded"

    fts_content = db.execute("SELECT fields_text FROM documents_fts_content WHERE document_id = ?", ("fts_promotion",)).fetchone()
    assert "Billing Reference (identifier): ENV 100002966355" in fts_content["fields_text"]

    results = fulltext_search(db, "ENV", limit=5, filters={"promotion:billing_reference": "%ENV%"})
    assert results
    assert results[0].document_id == "fts_promotion"


def test_fulltext_search_prefers_normalized_free_text(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    json_path = make_input_pair(
        "fts_normalized",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )
    assert load_from_file(db, json_path).status == "loaded"

    assert fulltext_search(db, "Faellig", limit=5) == []
    results = fulltext_search(db, "Schlussrechnung", limit=5)
    assert results
    assert results[0].document_id == "fts_normalized"


def test_fulltext_search_uses_fallback_text_when_free_text_missing(
    db,
    mixed_structured,
    legacy_validation_report,
    make_input_pair,
):
    json_path = make_input_pair("fts_fallback", mixed_structured, legacy_report=legacy_validation_report)
    assert load_from_file(db, json_path).status == "loaded"

    results = fulltext_search(db, "Wasser", limit=5)
    assert results
    assert results[0].document_id == "fts_fallback"


def test_fulltext_search_returns_empty_for_invalid_fts_syntax(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
):
    json_path = make_input_pair("fts_invalid", vision_structured, vision_report=vision_validation_report)
    assert load_from_file(db, json_path).status == "loaded"

    assert fulltext_search(db, '"', limit=5) == []
