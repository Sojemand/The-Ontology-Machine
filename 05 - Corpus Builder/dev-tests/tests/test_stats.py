"""Stats tests for Corpus Builder Vision."""

from __future__ import annotations

from pathlib import Path

from corpus_builder.loader import load_from_file as _load_from_file
from corpus_builder.stats import corpus_stats, format_stats, print_stats
from .semantic_release_test_support import build_release_variant


def _report_path(json_path: Path) -> Path:
    for suffix in (".vision_validation_report.json", ".validation_report.json"):
        candidate = json_path.with_name(json_path.name.replace(".structured.json", suffix))
        if candidate.exists():
            return candidate
    return json_path.with_name(json_path.name.replace(".structured.json", ".vision_validation_report.json"))


def load_from_file(db, json_path: Path, *, semantic_release=None):
    normalized_path = json_path.with_name(json_path.name.replace(".structured.json", ".structured.normalized.json"))
    return _load_from_file(
        db,
        normalized_path,
        _report_path(json_path),
        structured_path=json_path,
        semantic_release=semantic_release,
    )


def test_corpus_stats_reflect_loaded_documents(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    mixed_structured,
    legacy_validation_report,
    make_input_pair,
):
    vision_path = make_input_pair("stats_vision", vision_structured, vision_report=vision_validation_report, normalized=vision_normalized)
    mixed_path = make_input_pair("stats_mixed", mixed_structured, legacy_report=legacy_validation_report)
    assert load_from_file(db, vision_path, semantic_release=build_release_variant()).status == "loaded"
    assert load_from_file(db, mixed_path).status == "loaded"

    stats = corpus_stats(db)

    assert stats["total_documents"] == 2
    assert stats["by_document_type"]["invoice"] == 1
    assert stats["by_document_type"]["spreadsheet"] == 1
    assert stats["by_validator_status"]["pass"] == 1
    assert stats["by_validator_status"]["warn"] == 1
    assert stats["by_promotion_slot"]["billing_reference"] == 1
    assert any(name.startswith("billing_reference: ENV") for name, _count in stats["top_promotion_values"])


def test_format_stats_renders_required_and_optional_sections() -> None:
    stats = {
        "total_documents": 2,
        "total_archived": 1,
        "total_fields": 5,
        "total_relations": 3,
        "total_entities": 4,
        "stale_documents": 1,
        "has_embeddings": True,
        "embeddings_count": 7,
        "by_document_type": {"invoice": 2},
        "by_category": {},
        "by_language": {},
        "by_validator_status": {},
        "by_promotion_slot": {"billing_reference": 2},
        "by_projection": {},
        "by_materialization_state": {},
        "by_entity_type": {"organization": 4},
        "top_tags": [("energy", 3)],
        "top_people": [],
        "top_organizations": [],
        "top_field_keys": [],
        "top_promotion_values": [("billing_reference: A-1", 2)],
        "avg_confidence": 0.91,
        "avg_fields_per_doc": 2.5,
        "promotion_numeric_totals": {"amount_due": 1234.5},
        "date_range": {"earliest": "2026-01-01", "latest": "2026-01-31"},
    }

    text = format_stats(stats)

    assert "CORPUS STATISTIKEN" in text
    assert "Dokumente:     2" in text
    assert "Avg Konfidenz: 0.91" in text
    assert "Avg Fields:    2.5" in text
    assert "Zeitraum:      2026-01-01 - 2026-01-31" in text
    assert "Dokumenttypen:" in text
    assert "Entity-Typen:" in text
    assert "Promotion Slots:" in text
    assert "Top Tags:" in text
    assert "Top Promotions:" in text


def test_format_stats_omits_empty_optional_sections() -> None:
    stats = {
        "total_documents": 0,
        "total_archived": 0,
        "total_fields": 0,
        "total_relations": 0,
        "total_entities": 0,
        "stale_documents": 0,
        "has_embeddings": False,
        "embeddings_count": 0,
        "by_document_type": {},
        "by_category": {},
        "by_language": {},
        "by_validator_status": {},
        "by_promotion_slot": {},
        "by_projection": {},
        "by_materialization_state": {},
        "by_entity_type": {},
        "top_tags": [],
        "top_people": [],
        "top_organizations": [],
        "top_field_keys": [],
        "top_promotion_values": [],
        "avg_confidence": None,
        "avg_fields_per_doc": None,
        "promotion_numeric_totals": {},
        "date_range": {"earliest": None, "latest": None},
    }

    text = format_stats(stats)

    assert "Avg Konfidenz" not in text
    assert "Avg Fields" not in text
    assert "Zeitraum" not in text


def test_print_stats_writes_report_to_stdout(capsys) -> None:
    stats = {
        "total_documents": 1,
        "total_archived": 0,
        "total_fields": 0,
        "total_relations": 0,
        "total_entities": 0,
        "stale_documents": 0,
        "has_embeddings": False,
        "embeddings_count": 0,
        "by_document_type": {},
        "by_category": {},
        "by_language": {},
        "by_validator_status": {},
        "by_promotion_slot": {},
        "by_projection": {},
        "by_materialization_state": {},
        "by_entity_type": {},
        "top_tags": [],
        "top_people": [],
        "top_organizations": [],
        "top_field_keys": [],
        "top_promotion_values": [],
        "avg_confidence": None,
        "avg_fields_per_doc": None,
        "promotion_numeric_totals": {},
        "date_range": {"earliest": None, "latest": None},
    }

    print_stats(stats)

    output = capsys.readouterr().out
    assert output.startswith("\n")
    assert "CORPUS STATISTIKEN" in output
    assert "Dokumente:     1" in output
