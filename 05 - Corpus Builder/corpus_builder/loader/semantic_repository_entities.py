"""Entity, attribute and relation writes for semantic materialization."""

from __future__ import annotations

import sqlite3

from ..models.serialization import now_iso
from .semantic_repository_evidence import (
    SUBJECT_DOCUMENT_ENTITY,
    SUBJECT_ENTITY_ATTRIBUTE,
    SUBJECT_ENTITY_RELATION,
    _insert_semantic_evidence_links,
    _semantic_atom_ids,
    _sqlite_safe,
)
from .types import JsonDict


def insert_document_entities(conn: sqlite3.Connection, document_id: str, materialized: JsonDict, *, evidence_index: JsonDict | None = None) -> None:
    entity_ids: dict[str, int] = {}
    for entity in materialized.get("entities", []) or []:
        cursor = conn.execute(
            "INSERT INTO document_entities (document_id, entity_key, entity_type, role_type, display_value, normalized_value, source_path, row_index, page, sequence, projection_id, materialization_version, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                document_id,
                entity.get("entity_key"),
                entity.get("entity_type"),
                entity.get("role_type"),
                entity.get("display_value"),
                entity.get("normalized_value"),
                entity.get("source_path"),
                entity.get("row_index"),
                entity.get("page"),
                entity.get("sequence"),
                entity.get("projection_id"),
                entity.get("materialization_version"),
                entity.get("state"),
            ),
        )
        entity_id = int(cursor.lastrowid)
        entity_ids[str(entity.get("entity_key"))] = entity_id
        _insert_semantic_evidence_links(
            conn,
            SUBJECT_DOCUMENT_ENTITY,
            entity_id,
            _semantic_atom_ids(entity, evidence_index, include_prefix=True, entity_key=str(entity.get("entity_key") or "")),
            "source",
        )
    _insert_entity_attributes(conn, entity_ids, materialized, evidence_index=evidence_index)
    _insert_entity_relations(conn, document_id, entity_ids, materialized, evidence_index=evidence_index)


def _insert_entity_attributes(conn: sqlite3.Connection, entity_ids: dict[str, int], materialized: JsonDict, *, evidence_index: JsonDict | None = None) -> None:
    for attribute in materialized.get("entity_attributes", []) or []:
        entity_id = entity_ids.get(str(attribute.get("entity_key")))
        if entity_id is None:
            continue
        cursor = conn.execute(
            "INSERT INTO entity_attributes (entity_id, attribute_code, display_value, normalized_value, numeric_value, date_value, value_json, source_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entity_id, attribute.get("attribute_code"), attribute.get("display_value"), attribute.get("normalized_value"), attribute.get("numeric_value"), attribute.get("date_value"), attribute.get("value_json"), attribute.get("source_path")),
        )
        _insert_semantic_evidence_links(
            conn,
            SUBJECT_ENTITY_ATTRIBUTE,
            int(cursor.lastrowid),
            _semantic_atom_ids(attribute, evidence_index, include_prefix=False),
            "value",
        )


def _insert_entity_relations(conn: sqlite3.Connection, document_id: str, entity_ids: dict[str, int], materialized: JsonDict, *, evidence_index: JsonDict | None = None) -> None:
    for relation in materialized.get("entity_relations", []) or []:
        source_path = _sqlite_safe(relation.get("source_path"))
        cursor = conn.execute(
            "INSERT INTO entity_relations (document_id, relation_type, source_entity_id, target_entity_id, target_document_id, target_hint, description, source_path, relation_origin, confidence, evidence_refs, inference_policy_version, status, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                document_id,
                relation.get("relation_type"),
                entity_ids.get(str(relation.get("source_entity_key"))),
                entity_ids.get(str(relation.get("target_entity_key"))),
                relation.get("target_document_id"),
                relation.get("target_hint"),
                relation.get("description"),
                source_path,
                relation.get("relation_origin") or "observed",
                relation.get("confidence"),
                _sqlite_safe(relation.get("evidence_refs") or source_path),
                relation.get("inference_policy_version"),
                relation.get("status") or "observed",
                relation.get("created_by") or "corpus_builder",
                relation.get("created_at") or now_iso(),
            ),
        )
        _insert_semantic_evidence_links(
            conn,
            SUBJECT_ENTITY_RELATION,
            int(cursor.lastrowid),
            _semantic_atom_ids(relation, evidence_index, include_prefix=True),
            "relation",
        )
