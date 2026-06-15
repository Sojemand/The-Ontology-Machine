"""Document graph copy workflow for corpus merges."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from ..database.repository_documents import get_fields_dict, get_orgs_list, get_people_list, get_rows_list, get_tags_list
from ..models.serialization import now_iso
from .merge_constants import COLLISION_ARCHIVE_EXISTING, COLLISION_OVERWRITE_EXISTING
from .merge_document_rows import (
    copy_candidate_evidence,
    copy_document_entities,
    copy_document_promotions,
    copy_entity_attributes,
    copy_entity_relations,
    copy_evidence_atoms,
    copy_semantic_evidence_links,
    copy_optional_single_row,
    copy_simple_rows,
    copy_slot_candidates,
    insert_dynamic_row,
)
from .merge_preflight import document_ids


def merge_documents(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, *, collision_decision: str) -> dict[str, int]:
    source_document_ids = sorted(document_ids(source_conn))
    collisions = sorted(document_ids(source_conn) & document_ids(target_conn))
    archived_collisions = 0
    overwritten_collisions = 0
    if collision_decision == COLLISION_ARCHIVE_EXISTING:
        archive_ids = {doc_id: unique_archive_id(target_conn, document_id=doc_id, content_hash=document_content_hash(target_conn, doc_id)) for doc_id in collisions}
        for doc_id in collisions:
            archive_existing_collision(target_conn, doc_id, archive_id=archive_ids[doc_id], archive_rewrite_map=archive_ids)
            archived_collisions += 1
    elif collision_decision == COLLISION_OVERWRITE_EXISTING:
        for doc_id in collisions:
            delete_target_document(target_conn, doc_id)
            overwritten_collisions += 1
    elif collisions:
        raise ValueError("merge_collision_resolution_missing")
    for doc_id in source_document_ids:
        copy_document(source_conn, target_conn, doc_id)
        _loader_repository().log_history(target_conn, doc_id, "merged", details="source_db_import")
    return {
        "imported_document_count": len(source_document_ids),
        "archived_collision_count": archived_collisions,
        "overwritten_collision_count": overwritten_collisions,
    }


def archive_existing_collision(
    target_conn: sqlite3.Connection,
    document_id: str,
    *,
    archive_id: str,
    archive_rewrite_map: dict[str, str],
) -> None:
    row = target_conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        return
    archived_at = now_iso()
    copy_document(
        target_conn,
        target_conn,
        document_id,
        target_document_id=archive_id,
        include_fts=False,
        document_overrides={
            "id": archive_id,
            "is_archived": 1,
            "archived_at": str(row["archived_at"] or "").strip() or archived_at,
            "superseded_by": document_id,
            "updated_at": archived_at,
        },
        relation_target_rewrite_map=archive_rewrite_map,
    )
    delete_target_document(target_conn, document_id)


def copy_document(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    document_id: str,
    *,
    target_document_id: str | None = None,
    include_fts: bool = True,
    document_overrides: dict[str, Any] | None = None,
    relation_target_rewrite_map: dict[str, str] | None = None,
) -> None:
    target_id = target_document_id or document_id
    row = source_conn.execute("SELECT * FROM documents WHERE id = ? LIMIT 1", (document_id,)).fetchone()
    if row is None:
        raise ValueError(f"Quelldokument fehlt waehrend Merge: {document_id}")
    payload = dict(row)
    payload["id"] = target_id
    payload.update(document_overrides or {})
    insert_dynamic_row(target_conn, "documents", payload)
    replacements = {"document_id": target_id}
    _copy_document_payloads(source_conn, target_conn, document_id, replacements, relation_target_rewrite_map)
    atom_map = copy_evidence_atoms(source_conn, target_conn, document_id, target_document_id=target_id)
    candidate_map = copy_slot_candidates(source_conn, target_conn, document_id, target_document_id=target_id)
    copy_candidate_evidence(source_conn, target_conn, atom_map=atom_map, candidate_map=candidate_map)
    copy_document_promotions(source_conn, target_conn, document_id, target_document_id=target_id, candidate_map=candidate_map)
    entity_map = copy_document_entities(source_conn, target_conn, document_id, target_document_id=target_id)
    attribute_map = copy_entity_attributes(source_conn, target_conn, entity_map=entity_map)
    relation_map = copy_entity_relations(source_conn, target_conn, document_id, target_document_id=target_id, entity_map=entity_map, relation_target_rewrite_map=relation_target_rewrite_map)
    copy_semantic_evidence_links(source_conn, target_conn, atom_map=atom_map, entity_map=entity_map, attribute_map=attribute_map, relation_map=relation_map)
    if include_fts:
        _insert_fts_from_source(source_conn, target_conn, dict(row), document_id, target_id)


def _copy_document_payloads(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    document_id: str,
    replacements: dict[str, Any],
    relation_target_rewrite_map: dict[str, str] | None,
) -> None:
    copy_optional_single_row(source_conn, target_conn, "document_payloads", "document_id", document_id, replace_values=replacements)
    for table in ("extracted_fields", "extracted_rows", "relations", "load_history", "materialization_audit"):
        pk = {"id"} if table != "materialization_audit" else {"audit_id"}
        copy_simple_rows(source_conn, target_conn, table, "document_id", document_id, exclude_columns=pk, replace_values=replacements, relation_target_rewrite_map=relation_target_rewrite_map)
    for table in ("tags", "people", "organizations", "document_page_images"):
        copy_simple_rows(source_conn, target_conn, table, "document_id", document_id, replace_values=replacements)
    copy_optional_single_row(source_conn, target_conn, "embeddings", "document_id", document_id, replace_values=replacements)
    copy_optional_single_row(source_conn, target_conn, "document_processing_state", "document_id", document_id, replace_values=replacements)


def unique_archive_id(target_conn: sqlite3.Connection, *, document_id: str, content_hash: str) -> str:
    suffix = hashlib.sha256(f"{document_id}:{content_hash}".encode("utf-8")).hexdigest()[:12]
    candidate = f"{document_id}__merge_archive__{suffix}"
    index = 1
    while target_conn.execute("SELECT 1 FROM documents WHERE id = ? LIMIT 1", (candidate,)).fetchone() is not None:
        candidate = f"{document_id}__merge_archive__{suffix}_{index}"
        index += 1
    return candidate


def document_content_hash(target_conn: sqlite3.Connection, document_id: str) -> str:
    row = target_conn.execute("SELECT content_hash FROM documents WHERE id = ? LIMIT 1", (document_id,)).fetchone()
    return str(row["content_hash"] or "").strip() if row is not None else ""


def delete_target_document(target_conn: sqlite3.Connection, document_id: str) -> None:
    _loader_repository().remove_from_fts(target_conn, document_id)
    target_conn.execute("DELETE FROM load_history WHERE document_id = ?", (document_id,))
    target_conn.execute("DELETE FROM materialization_audit WHERE document_id = ?", (document_id,))
    target_conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))


def _insert_fts_from_source(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, row: dict[str, Any], source_id: str, target_id: str) -> None:
    row["id"] = target_id
    _loader_repository().insert_fts_entry(
        target_conn,
        target_id,
        row,
        get_fields_dict(source_conn, source_id),
        get_rows_list(source_conn, source_id),
        [],
        get_tags_list(source_conn, source_id),
        get_people_list(source_conn, source_id),
        get_orgs_list(source_conn, source_id),
        promotions=_fetch_document_promotions(source_conn, source_id),
    )


def _fetch_document_promotions(source_conn: sqlite3.Connection, document_id: str) -> list[dict[str, Any]]:
    rows = source_conn.execute(
        "SELECT * FROM document_promotions WHERE document_id = ? AND is_current = 1 ORDER BY ordinal, promotion_id",
        (document_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _loader_repository():
    from ..loader import repository as loader_repository

    return loader_repository


__all__ = ["merge_documents"]
