from __future__ import annotations

import sqlite3
from typing import Any

from .ontology_validation_support import _check, _error, _rows


def validate_base_graph(conn: sqlite3.Connection, report: dict[str, Any]) -> None:
    _validate_foreign_keys(conn, report)
    _validate_source_document_pages(conn, report)
    _validate_source_document_classifications(conn, report)
    _validate_structural_units(conn, report)


def _validate_foreign_keys(conn: sqlite3.Connection, report: dict[str, Any]) -> None:
    rows = _rows(conn, "PRAGMA foreign_key_check")
    _check(report, "foreign_key_check", not rows, {"violations": rows})
    if rows:
        _error(report, "foreign_key_violation", "SQLite foreign_key_check found ontology/corpus reference violations.")


def _validate_source_document_pages(conn: sqlite3.Connection, report: dict[str, Any]) -> None:
    mismatches = _rows(
        conn,
        "SELECT sdp.document_id, sdp.source_document_id, d.source_document_id AS document_source_document_id, "
        "sdp.page_index, d.page_index AS document_page_index "
        "FROM source_document_pages sdp JOIN documents d ON d.id = sdp.document_id "
        "WHERE sdp.source_document_id != d.source_document_id OR sdp.page_index != d.page_index",
    )
    _check(report, "source_document_page_consistency", not mismatches, {"mismatches": mismatches})
    if mismatches:
        _error(report, "source_document_page_mismatch", "source_document_pages no longer matches documents source identity.")


def _validate_source_document_classifications(conn: sqlite3.Connection, report: dict[str, Any]) -> None:
    missing_base_release = _rows(
        conn,
        "SELECT sd.source_document_id, required.scope AS missing_scope "
        "FROM source_documents sd "
        "CROSS JOIN (SELECT 'base' AS scope UNION ALL SELECT 'semantic_release') required "
        "LEFT JOIN source_document_classifications cls ON cls.source_document_id = sd.source_document_id "
        "AND cls.classification_scope = required.scope AND cls.ontology_id IS NULL "
        "WHERE cls.source_document_id IS NULL",
    )
    _check(
        report,
        "source_document_base_release_classifications_exist",
        not missing_base_release,
        {"missing_classifications": missing_base_release},
    )
    if missing_base_release:
        _error(
            report,
            "missing_source_document_classifications",
            "Every source_document must have deterministic base and semantic_release classification rows.",
        )

    ontology_without_lens = _rows(
        conn,
        "SELECT cls.source_document_id, cls.ontology_id "
        "FROM source_document_classifications cls "
        "LEFT JOIN ontology_lenses lens ON lens.ontology_id = cls.ontology_id "
        "WHERE cls.classification_scope = 'ontology' AND lens.ontology_id IS NULL",
    )
    _check(
        report,
        "source_document_ontology_classification_lenses_exist",
        not ontology_without_lens,
        {"missing_lenses": ontology_without_lens},
    )
    if ontology_without_lens:
        _error(
            report,
            "missing_source_document_classification_lens",
            "Ontology-scoped source document classifications must reference an existing ontology lens.",
        )


def _validate_structural_units(conn: sqlite3.Connection, report: dict[str, Any]) -> None:
    missing_base_units = _rows(
        conn,
        "SELECT sd.source_document_id FROM source_documents sd "
        "LEFT JOIN structural_units unit ON unit.source_document_id = sd.source_document_id "
        "AND unit.unit_type = 'base_unit' AND unit.parent_unit_id IS NULL "
        "WHERE unit.unit_id IS NULL",
    )
    _check(report, "structural_base_units_exist", not missing_base_units, {"missing_base_units": missing_base_units})
    if missing_base_units:
        _error(report, "missing_structural_base_units", "Every source_document must have one deterministic base_unit.")

    duplicate_base_units = _rows(
        conn,
        "SELECT source_document_id, COUNT(*) AS unit_count FROM structural_units "
        "WHERE unit_type = 'base_unit' AND parent_unit_id IS NULL "
        "GROUP BY source_document_id HAVING COUNT(*) != 1",
    )
    _check(report, "single_structural_base_unit_per_source", not duplicate_base_units, {"duplicate_base_units": duplicate_base_units})
    if duplicate_base_units:
        _error(report, "duplicate_structural_base_units", "Each source_document must have exactly one root base_unit.")

    missing_page_units = _rows(
        conn,
        "SELECT sdp.source_document_id, sdp.document_id, sdp.page_index "
        "FROM source_document_pages sdp "
        "LEFT JOIN structural_units unit ON unit.source_document_id = sdp.source_document_id "
        "AND unit.document_id = sdp.document_id AND unit.unit_type = 'page_unit' "
        "WHERE unit.unit_id IS NULL",
    )
    _check(report, "structural_page_units_exist", not missing_page_units, {"missing_page_units": missing_page_units})
    if missing_page_units:
        _error(report, "missing_structural_page_units", "Every source_document_page must have one deterministic page_unit.")

    page_unit_mismatches = _rows(
        conn,
        "SELECT unit.unit_id, unit.source_document_id, unit.document_id, unit.page_index, "
        "sdp.source_document_id AS page_source_document_id, sdp.page_index AS source_page_index "
        "FROM structural_units unit "
        "LEFT JOIN source_document_pages sdp ON sdp.document_id = unit.document_id "
        "WHERE unit.unit_type = 'page_unit' "
        "AND (sdp.document_id IS NULL OR sdp.source_document_id != unit.source_document_id OR sdp.page_index != unit.page_index)",
    )
    _check(report, "structural_page_units_match_pages", not page_unit_mismatches, {"mismatches": page_unit_mismatches})
    if page_unit_mismatches:
        _error(report, "structural_page_unit_mismatch", "page_unit rows must match source_document_pages.")

    missing_contains_relations = _rows(
        conn,
        "SELECT page.unit_id, page.source_document_id, page.document_id "
        "FROM structural_units page "
        "JOIN structural_units base ON base.source_document_id = page.source_document_id "
        "AND base.unit_type = 'base_unit' AND base.parent_unit_id IS NULL "
        "LEFT JOIN structural_unit_relations rel ON rel.source_unit_id = base.unit_id "
        "AND rel.target_unit_id = page.unit_id AND rel.relation_type = 'contains' "
        "WHERE page.unit_type = 'page_unit' AND rel.relation_id IS NULL",
    )
    _check(
        report,
        "structural_contains_relations_exist",
        not missing_contains_relations,
        {"missing_contains_relations": missing_contains_relations},
    )
    if missing_contains_relations:
        _error(report, "missing_structural_contains_relations", "Every page_unit must be contained by its base_unit.")


__all__ = ["validate_base_graph"]
