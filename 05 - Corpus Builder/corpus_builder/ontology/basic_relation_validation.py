from __future__ import annotations

import sqlite3
from typing import Any

from .basic_relation_support import as_dict


def validate_base_graph(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    _append_if_rows(warnings, "base_relation_targets", conn.execute(
        "SELECT id, document_id, target_document_id FROM relations "
        "WHERE relation_origin = 'base_graph' "
        "AND target_document_id IS NOT NULL "
        "AND target_document_id NOT IN (SELECT id FROM documents)"
    ).fetchall())
    _append_if_rows(warnings, "source_document_page_consistency", conn.execute(
        "SELECT sdp.document_id, sdp.source_document_id, d.source_document_id AS document_source_document_id "
        "FROM source_document_pages sdp JOIN documents d ON d.id = sdp.document_id "
        "WHERE sdp.source_document_id != d.source_document_id OR sdp.page_index != d.page_index"
    ).fetchall())
    _append_if_rows(warnings, "structural_base_units", conn.execute(
        "SELECT sd.source_document_id FROM source_documents sd "
        "LEFT JOIN structural_units unit ON unit.source_document_id = sd.source_document_id "
        "AND unit.unit_type = 'base_unit' AND unit.parent_unit_id IS NULL "
        "WHERE unit.unit_id IS NULL"
    ).fetchall())
    _append_if_rows(warnings, "source_document_classifications", conn.execute(
        "SELECT sd.source_document_id, required.scope AS missing_scope "
        "FROM source_documents sd "
        "CROSS JOIN (SELECT 'base' AS scope UNION ALL SELECT 'semantic_release') required "
        "LEFT JOIN source_document_classifications cls ON cls.source_document_id = sd.source_document_id "
        "AND cls.classification_scope = required.scope AND cls.ontology_id IS NULL "
        "WHERE cls.source_document_id IS NULL"
    ).fetchall())
    _append_if_rows(warnings, "structural_page_units", conn.execute(
        "SELECT sdp.source_document_id, sdp.document_id, sdp.page_index "
        "FROM source_document_pages sdp "
        "LEFT JOIN structural_units unit ON unit.source_document_id = sdp.source_document_id "
        "AND unit.document_id = sdp.document_id AND unit.unit_type = 'page_unit' "
        "WHERE unit.unit_id IS NULL"
    ).fetchall())
    _append_if_rows(warnings, "structural_contains_relations", conn.execute(
        "SELECT page.unit_id, page.source_document_id, page.document_id "
        "FROM structural_units page "
        "JOIN structural_units base ON base.source_document_id = page.source_document_id "
        "AND base.unit_type = 'base_unit' AND base.parent_unit_id IS NULL "
        "LEFT JOIN structural_unit_relations rel ON rel.source_unit_id = base.unit_id "
        "AND rel.target_unit_id = page.unit_id AND rel.relation_type = 'contains' "
        "WHERE page.unit_type = 'page_unit' AND rel.relation_id IS NULL"
    ).fetchall())
    return warnings


def _append_if_rows(warnings: list[dict[str, Any]], check: str, rows: list[Any]) -> None:
    if rows:
        warnings.append({"check": check, "rows": [as_dict(row) for row in rows]})


__all__ = ["validate_base_graph"]
