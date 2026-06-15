"""Entity row copy helpers for corpus document merges."""

from __future__ import annotations

import sqlite3

from .merge_row_sql import insert_dynamic_row, rewrite_document_targets
from .sql_parameter_batches import iter_parameter_batches


def copy_document_entities(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    document_id: str,
    *,
    target_document_id: str,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    rows = source_conn.execute("SELECT * FROM document_entities WHERE document_id = ? ORDER BY entity_id", (document_id,)).fetchall()
    for row in rows:
        payload = dict(row)
        old_id = int(payload.pop("entity_id"))
        payload["document_id"] = target_document_id
        mapping[old_id] = insert_dynamic_row(target_conn, "document_entities", payload)
    return mapping


def copy_entity_attributes(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, *, entity_map: dict[int, int]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    if not entity_map:
        return mapping
    for entity_ids in iter_parameter_batches(entity_map):
        placeholders = ", ".join("?" for _ in entity_ids)
        rows = source_conn.execute(
            f"SELECT * FROM entity_attributes WHERE entity_id IN ({placeholders}) ORDER BY attribute_id",
            entity_ids,
        )
        for row in rows:
            payload = dict(row)
            old_id = int(payload.pop("attribute_id"))
            payload["entity_id"] = entity_map[int(row["entity_id"])]
            mapping[old_id] = insert_dynamic_row(target_conn, "entity_attributes", payload)
    return mapping


def copy_entity_relations(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    document_id: str,
    *,
    target_document_id: str,
    entity_map: dict[int, int],
    relation_target_rewrite_map: dict[str, str] | None = None,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    rows = source_conn.execute("SELECT * FROM entity_relations WHERE document_id = ? ORDER BY relation_id", (document_id,)).fetchall()
    for row in rows:
        payload = dict(row)
        old_id = int(payload.pop("relation_id"))
        payload["document_id"] = target_document_id
        if payload.get("source_entity_id") is not None:
            payload["source_entity_id"] = entity_map.get(int(payload["source_entity_id"]))
        if payload.get("target_entity_id") is not None:
            payload["target_entity_id"] = entity_map.get(int(payload["target_entity_id"]))
        rewrite_document_targets(payload, relation_target_rewrite_map)
        mapping[old_id] = insert_dynamic_row(target_conn, "entity_relations", payload)
    return mapping


def copy_semantic_evidence_links(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    *,
    atom_map: dict[int, int],
    entity_map: dict[int, int],
    attribute_map: dict[int, int],
    relation_map: dict[int, int],
) -> None:
    if not atom_map:
        return
    subject_maps = {
        "document_entity": entity_map,
        "entity_attribute": attribute_map,
        "entity_relation": relation_map,
    }
    for subject_kind, subject_map in subject_maps.items():
        if not subject_map:
            continue
        for subject_ids in iter_parameter_batches(subject_map, reserved_parameters=1):
            placeholders = ", ".join("?" for _ in subject_ids)
            rows = source_conn.execute(
                f"SELECT subject_kind, subject_id, atom_id, evidence_role FROM semantic_evidence_links "
                f"WHERE subject_kind = ? AND subject_id IN ({placeholders}) "
                "ORDER BY subject_id, atom_id, evidence_role",
                (subject_kind, *subject_ids),
            )
            for row in rows:
                atom_id = atom_map.get(int(row["atom_id"]))
                subject_id = subject_map.get(int(row["subject_id"]))
                if atom_id is None or subject_id is None:
                    continue
                target_conn.execute(
                    "INSERT OR IGNORE INTO semantic_evidence_links (subject_kind, subject_id, atom_id, evidence_role) VALUES (?, ?, ?, ?)",
                    (row["subject_kind"], subject_id, atom_id, row["evidence_role"]),
                )
