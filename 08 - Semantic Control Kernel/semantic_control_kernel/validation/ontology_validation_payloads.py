from __future__ import annotations

import json
import sqlite3
from typing import Any

from .ontology_validation_support import JSON_COLUMNS, _check, _error, _ontology_clause, _rows


def validate_ontology_payloads(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    _validate_evidence_targets(conn, report, ontology_id=ontology_id)
    _validate_evidence_refs(conn, report, ontology_id=ontology_id)
    _validate_embedding_chunk_targets(conn, report, ontology_id=ontology_id)
    _validate_json_columns(conn, report, ontology_id=ontology_id)


def _validate_evidence_targets(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    checks = (
        ("term", "ontology_terms", "term_id"),
        ("node", "ontology_nodes", "node_id"),
        ("edge", "ontology_edges", "edge_id"),
        ("assertion", "ontology_assertions", "assertion_id"),
        ("relation", "relations", "id"),
    )
    missing: list[dict[str, Any]] = []
    for target_type, table_name, key_column in checks:
        clause, params = _ontology_clause("link", ontology_id)
        missing.extend(
            _rows(
                conn,
                "SELECT link.evidence_link_id, link.ontology_id, link.target_type, link.target_id "
                "FROM ontology_evidence_links link "
                f"LEFT JOIN {table_name} target ON CAST(target.{key_column} AS TEXT) = link.target_id "
                f"WHERE link.target_type = ? AND target.{key_column} IS NULL{clause}",
                (target_type, *params),
            )
        )
    _check(report, "evidence_targets_exist", not missing, {"missing_targets": missing})
    if missing:
        _error(report, "missing_evidence_targets", "Ontology evidence links reference missing target objects.")


def _validate_evidence_refs(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    checks = (
        ("document", "documents", "id"),
        ("source_document", "source_documents", "source_document_id"),
        ("structural_unit", "structural_units", "unit_id"),
        ("evidence_atom", "evidence_atoms", "atom_id"),
        ("promotion", "document_promotions", "promotion_id"),
        ("field", "extracted_fields", "id"),
        ("row", "extracted_rows", "id"),
    )
    missing: list[dict[str, Any]] = []
    for evidence_ref_type, table_name, key_column in checks:
        clause, params = _ontology_clause("link", ontology_id)
        missing.extend(
            _rows(
                conn,
                "SELECT link.evidence_link_id, link.ontology_id, link.evidence_ref_type, link.evidence_ref_id "
                "FROM ontology_evidence_links link "
                f"LEFT JOIN {table_name} ref ON CAST(ref.{key_column} AS TEXT) = link.evidence_ref_id "
                f"WHERE link.evidence_ref_type = ? AND ref.{key_column} IS NULL{clause}",
                (evidence_ref_type, *params),
            )
        )
    _check(report, "evidence_refs_exist", not missing, {"missing_refs": missing})
    if missing:
        _error(report, "missing_evidence_refs", "Ontology evidence links reference missing corpus evidence.")


def _validate_embedding_chunk_targets(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    checks = (
        ("term", "ontology_terms", "term_id"),
        ("node", "ontology_nodes", "node_id"),
        ("edge", "ontology_edges", "edge_id"),
        ("assertion", "ontology_assertions", "assertion_id"),
        ("lens", "ontology_lenses", "ontology_id"),
    )
    missing: list[dict[str, Any]] = []
    for object_type, table_name, key_column in checks:
        clause, params = _ontology_clause("chunk", ontology_id)
        missing.extend(
            _rows(
                conn,
                "SELECT chunk.chunk_id, chunk.ontology_id, chunk.object_type, chunk.object_id "
                "FROM ontology_embedding_chunks chunk "
                f"LEFT JOIN {table_name} target ON CAST(target.{key_column} AS TEXT) = chunk.object_id "
                f"WHERE chunk.object_type = ? AND target.{key_column} IS NULL{clause}",
                (object_type, *params),
            )
        )
    _check(report, "embedding_chunk_targets_exist", not missing, {"missing_targets": missing})
    if missing:
        _error(report, "missing_embedding_chunk_targets", "Ontology embedding chunks reference missing ontology objects.")


def _validate_json_columns(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    invalid: list[dict[str, Any]] = []
    for table_name, id_column, json_column in JSON_COLUMNS:
        if ontology_id and table_name.startswith("ontology_") and table_name not in {"ontology_lenses", "ontology_edit_log"}:
            rows = conn.execute(
                f"SELECT {id_column} AS row_id, {json_column} AS json_text FROM {table_name} WHERE ontology_id = ?",
                (ontology_id,),
            ).fetchall()
        elif ontology_id and table_name == "ontology_lenses":
            rows = conn.execute(
                f"SELECT {id_column} AS row_id, {json_column} AS json_text FROM {table_name} WHERE ontology_id = ?",
                (ontology_id,),
            ).fetchall()
        elif ontology_id and table_name == "ontology_edit_log":
            rows = conn.execute(
                f"SELECT {id_column} AS row_id, {json_column} AS json_text FROM {table_name} WHERE ontology_id = ? OR ontology_id IS NULL",
                (ontology_id,),
            ).fetchall()
        else:
            rows = conn.execute(f"SELECT {id_column} AS row_id, {json_column} AS json_text FROM {table_name}").fetchall()
        for row in rows:
            try:
                json.loads(str(row["json_text"] or ""))
            except json.JSONDecodeError:
                invalid.append({"table": table_name, "row_id": row["row_id"], "column": json_column})
    _check(report, "json_columns_valid", not invalid, {"invalid_json": invalid})
    if invalid:
        _error(report, "invalid_json_columns", "Ontology JSON columns must contain valid JSON.")


__all__ = ["validate_ontology_payloads"]
