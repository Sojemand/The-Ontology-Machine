from __future__ import annotations

import sqlite3
from typing import Any

from .ontology_validation_support import (
    _check,
    _error,
    _missing_semantic_refs,
    _ontology_clause,
    _rows,
)


def validate_ontology_objects(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    _validate_required_identifiers(conn, report)
    _validate_activation(conn, report)
    _validate_edge_lens_consistency(conn, report, ontology_id=ontology_id)
    _validate_node_source_refs(conn, report, ontology_id=ontology_id)
    _validate_assertion_refs(conn, report, ontology_id=ontology_id)
    _validate_verified_objects_have_evidence(conn, report, ontology_id=ontology_id)


def _validate_required_identifiers(conn: sqlite3.Connection, report: dict[str, Any]) -> None:
    required_columns = (
        ("structural_units", "unit_id"),
        ("structural_unit_relations", "relation_id"),
        ("ontology_lenses", "ontology_id"),
        ("ontology_runs", "run_id"),
        ("ontology_terms", "term_id"),
        ("ontology_nodes", "node_id"),
        ("ontology_edges", "edge_id"),
        ("ontology_assertions", "assertion_id"),
        ("ontology_evidence_links", "evidence_link_id"),
        ("ontology_embedding_chunks", "chunk_id"),
    )
    missing: list[dict[str, Any]] = []
    for table_name, id_column in required_columns:
        missing.extend(
            _rows(
                conn,
                f"SELECT '{table_name}' AS table_name, rowid, '{id_column}' AS id_column "
                f"FROM {table_name} WHERE {id_column} IS NULL OR TRIM(CAST({id_column} AS TEXT)) = ''",
            )
        )
    _check(report, "required_object_identifiers", not missing, {"missing_identifiers": missing})
    if missing:
        _error(report, "missing_required_object_identifiers", "Ontology objects must have stable non-empty primary identifiers.")


def _validate_activation(conn: sqlite3.Connection, report: dict[str, Any]) -> None:
    active_lenses = _rows(
        conn,
        "SELECT activation.ontology_id, activation.is_primary, lens.status FROM ontology_activation activation "
        "JOIN ontology_lenses lens ON lens.ontology_id = activation.ontology_id "
        "WHERE activation.is_active = 1 AND lens.status != 'archived'",
    )
    active_primary = [row for row in active_lenses if int(row.get("is_primary") or 0) == 1]
    _check(
        report,
        "single_primary_lens",
        not active_lenses or len(active_primary) == 1,
        {"active_lenses": active_lenses, "active_primary": active_primary},
    )
    if len(active_primary) > 1:
        _error(report, "multiple_primary_lenses", "More than one active primary ontology lens exists.")
    if active_lenses and not active_primary:
        _error(report, "no_primary_lens", "At least one ontology lens is active, but no active primary lens is selected.")
    not_ready_primary = [row for row in active_primary if row.get("status") != "ready"]
    _check(report, "active_primary_ready", not not_ready_primary, {"not_ready_primary": not_ready_primary})
    if not_ready_primary:
        _error(report, "primary_lens_not_ready", "Active primary ontology lenses must have status 'ready'.")

    dangling = _rows(
        conn,
        "SELECT activation.ontology_id FROM ontology_activation activation "
        "LEFT JOIN ontology_lenses lens ON lens.ontology_id = activation.ontology_id "
        "WHERE lens.ontology_id IS NULL",
    )
    _check(report, "activation_refs_exist", not dangling, {"dangling_activation": dangling})
    if dangling:
        _error(report, "dangling_activation", "ontology_activation references missing ontology lenses.")


def _validate_edge_lens_consistency(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    clause, params = _ontology_clause("edge", ontology_id)
    rows = _rows(
        conn,
        "SELECT edge.edge_id, edge.ontology_id, source.ontology_id AS source_ontology_id, "
        "target.ontology_id AS target_ontology_id "
        "FROM ontology_edges edge "
        "JOIN ontology_nodes source ON source.node_id = edge.source_node_id "
        "JOIN ontology_nodes target ON target.node_id = edge.target_node_id "
        f"WHERE (source.ontology_id != edge.ontology_id OR target.ontology_id != edge.ontology_id){clause}",
        params,
    )
    _check(report, "edge_lens_consistency", not rows, {"mismatched_edges": rows})
    if rows:
        _error(report, "edge_lens_mismatch", "Ontology edges must connect nodes from the same ontology lens.")


def _validate_node_source_refs(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    missing = _missing_semantic_refs(
        conn,
        source_table="ontology_nodes",
        source_alias="node",
        source_id_column="node_id",
        ref_type_column="source_ref_type",
        ref_id_column="source_ref_id",
        ontology_id=ontology_id,
    )
    _check(report, "node_source_refs_exist", not missing, {"missing_refs": missing})
    if missing:
        _error(report, "missing_node_source_refs", "Ontology node source_ref_type/source_ref_id values must reference existing corpus or ontology objects.")


def _validate_assertion_refs(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    missing_subjects = _missing_semantic_refs(
        conn,
        source_table="ontology_assertions",
        source_alias="assertion",
        source_id_column="assertion_id",
        ref_type_column="subject_ref_type",
        ref_id_column="subject_ref_id",
        ontology_id=ontology_id,
        required=True,
    )
    _check(report, "assertion_subject_refs_exist", not missing_subjects, {"missing_refs": missing_subjects})
    if missing_subjects:
        _error(report, "missing_assertion_subject_refs", "Ontology assertion subjects must reference existing corpus or ontology objects.")

    missing_objects = _missing_semantic_refs(
        conn,
        source_table="ontology_assertions",
        source_alias="assertion",
        source_id_column="assertion_id",
        ref_type_column="object_ref_type",
        ref_id_column="object_ref_id",
        ontology_id=ontology_id,
        require_complete_pair=True,
    )
    _check(report, "assertion_object_refs_exist", not missing_objects, {"missing_refs": missing_objects})
    if missing_objects:
        _error(report, "missing_assertion_object_refs", "Ontology assertion object_ref_type/object_ref_id values must reference existing corpus or ontology objects, or both be omitted when value_text is used.")


def _validate_verified_objects_have_evidence(
    conn: sqlite3.Connection,
    report: dict[str, Any],
    *,
    ontology_id: str | None,
) -> None:
    checks = (
        ("node", "ontology_nodes", "node_id"),
        ("edge", "ontology_edges", "edge_id"),
        ("assertion", "ontology_assertions", "assertion_id"),
    )
    missing: list[dict[str, Any]] = []
    for target_type, table_name, key_column in checks:
        clause, params = _ontology_clause("target", ontology_id)
        missing.extend(
            _rows(
                conn,
                f"SELECT '{target_type}' AS target_type, target.ontology_id, target.{key_column} AS target_id "
                f"FROM {table_name} target "
                "LEFT JOIN ontology_evidence_links link ON link.ontology_id = target.ontology_id "
                "AND link.target_type = ? AND link.target_id = CAST(target."
                f"{key_column} AS TEXT) "
                f"WHERE target.status = 'verified' AND link.evidence_link_id IS NULL{clause}",
                (target_type, *params),
            )
        )
    _check(report, "verified_objects_have_evidence", not missing, {"missing_evidence": missing})
    if missing:
        _error(report, "verified_objects_without_evidence", "Verified ontology nodes, edges and assertions must have at least one evidence link.")


__all__ = ["validate_ontology_objects"]
