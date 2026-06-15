"""Document-level load workflow for corpus materialization."""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Callable

from ..database import find_by_file_path
from ..models.results import LoadResult
from . import audit, page_image_workflow, policy, repository
from .candidate_links import link_candidate_evidence
from .document_record import build_document
from .field_values import extracted_field_values
from .mail_context import insert_mail_context_fields, sync_mail_relations
from .materialization import materialize, persisted_processing_state
from .observed_semantics import build_observed_semantics, split_relations
from .original_artifact import load_original_artifact
from .preparation import prepare_load_bundle, select_candidate_payload
from .types import JsonDict

logger = logging.getLogger(__name__)


def load_document(
    conn: sqlite3.Connection,
    document_id: str,
    structured_json: JsonDict | None,
    validation_report: JsonDict | None,
    content_hash: str,
    file_path: str,
    normalized_json: JsonDict | None = None,
    *,
    raw_json: JsonDict | None = None,
    semantic_release: JsonDict | None = None,
    insert_fts_entry_fn: Callable[..., None] = repository.insert_fts_entry,
    persist_page_images_in_db: bool = False,
    page_images_dir: str | Path | None = None,
    persist_original_artifact_in_db: bool = False,
    max_original_artifact_bytes: int | None = 52428800,
    max_page_image_bytes: int | None = 10485760,
    max_page_image_total_bytes: int | None = 104857600,
    artifact_hint_path: Path | None = None,
) -> LoadResult:
    try:
        prepared = prepare_load_bundle(structured_json, normalized_json, validation_report)
        projection_meta, materialized = materialize(document_id, prepared.preferred_json, normalized_json, semantic_release, prepared.source_mode, validate_release=True)
        persisted_state = persisted_processing_state(document_id, projection_meta, materialized, semantic_release, prepared.source_mode)
        doc = build_document(
            document_id,
            prepared,
            content_hash,
            file_path,
            normalized_json=normalized_json,
            projection_meta=materialized or projection_meta,
            release=semantic_release,
        )

        conn.execute("BEGIN IMMEDIATE")
        was_archived, existing_by_path = False, None
        existing_by_id = conn.execute("SELECT id, file_path, content_hash, is_archived FROM documents WHERE id = ?", (document_id,)).fetchone()
        if existing_by_id:
            if existing_by_id["file_path"] != file_path:
                raise ValueError(f"document_id collision: {document_id} verweist bereits auf {existing_by_id['file_path']}")
            if existing_by_id["content_hash"] == content_hash:
                conn.rollback()
                return LoadResult(status="skipped", document_id=document_id, reason="identical")
            repository.clear_incoming_document_links(conn, existing_by_id["id"])
            repository.remove_from_fts(conn, existing_by_id["id"])
            conn.execute("DELETE FROM documents WHERE id = ?", (existing_by_id["id"],))
            was_archived = not bool(existing_by_id["is_archived"])
        else:
            existing_by_path = find_by_file_path(conn, file_path)
            if existing_by_path and existing_by_path["id"] != document_id:
                if existing_by_path["content_hash"] == content_hash:
                    conn.rollback()
                    return LoadResult(status="skipped", document_id=document_id, reason="duplicate_file_path")
                repository.archive_document(conn, existing_by_path["id"])
                repository.log_history(conn, existing_by_path["id"], "archived", old_hash=existing_by_path["content_hash"], new_hash=content_hash)
                was_archived = True

        repository.insert_document(conn, doc)
        if was_archived and existing_by_path:
            conn.execute("UPDATE documents SET superseded_by = ? WHERE id = ?", (document_id, existing_by_path["id"]))
        for key, value in prepared.sanitized_fields.items():
            provenance = prepared.field_provenance.get(key)
            for field_value in extracted_field_values(value):
                repository.insert_field(
                    conn,
                    document_id,
                    key,
                    field_value,
                    confidence=provenance[0] if provenance else None,
                    source=provenance[1] if provenance else None,
                )
        mail_context = insert_mail_context_fields(conn, document_id, prepared)
        for index, row in enumerate(prepared.sanitized_rows):
            repository.insert_row(conn, document_id, index, row)
        document_relations, graph_relations = split_relations(prepared.sanitized_relations)
        for relation in document_relations:
            repository.insert_relation(conn, document_id, relation)
        sync_mail_relations(conn, document_id, mail_context)
        for table, values in (("tags", prepared.tags), ("people", prepared.people), ("organizations", prepared.orgs)):
            for value in values:
                repository.insert_normalized(conn, table, document_id, value)
        original_file_name, original_media_type, original_blob = load_original_artifact(
            file_path,
            enabled=persist_original_artifact_in_db,
            max_bytes=max_original_artifact_bytes,
        )
        repository.insert_document_payload(
            conn,
            document_id,
            prepared.structured_payload or None,
            normalized_json,
            raw_json=raw_json,
            release_fingerprint=str(semantic_release.get("fingerprint") or "") if isinstance(semantic_release, dict) else None,
            free_text=doc.get("content_free_text"),
            original_file_name=original_file_name,
            original_media_type=original_media_type,
            original_blob=original_blob,
        )
        page_image_workflow.persist_document_page_images(
            conn,
            document_id,
            doc,
            enabled=persist_page_images_in_db,
            page_images_dir=page_images_dir,
            artifact_hint_path=artifact_hint_path,
            max_image_bytes=max_page_image_bytes,
            max_total_bytes=max_page_image_total_bytes,
        )

        path_atom_ids: dict[str, list[int]] = defaultdict(list)
        source_ref_atom_ids: dict[str, list[int]] = defaultdict(list)
        anchor_atom_ids: dict[tuple[str, str], list[int]] = defaultdict(list)
        for atom in audit.build_evidence_atoms(prepared.evidence_payload, page_count=doc.get("page_count")):
            atom_id = repository.insert_evidence_atom(conn, document_id, atom)
            path_atom_ids[str(atom.get("json_path") or "")].append(atom_id)
            if atom.get("source_ref"):
                source_ref_atom_ids[str(atom["source_ref"])].append(atom_id)
            if atom.get("anchor_kind") and atom.get("anchor_key"):
                anchor_atom_ids[(str(atom["anchor_kind"]), str(atom["anchor_key"]))].append(atom_id)
        evidence_index = {"paths": path_atom_ids, "source_refs": source_ref_atom_ids, "anchors": anchor_atom_ids}
        candidate_payload = select_candidate_payload(prepared.preferred_json, prepared.structured_payload)
        promotion_candidate_ids: dict[int, int] = {}
        for candidate in policy.build_slot_candidates(candidate_payload, doc, prepared.sanitized_fields, prepared.sanitized_rows, prepared.tags, prepared.people, prepared.orgs, seed_candidates=(materialized or {}).get("slot_candidates")):
            candidate_id = repository.insert_slot_candidate(conn, document_id, candidate)
            link_candidate_evidence(conn, candidate_id, candidate, path_atom_ids, source_ref_atom_ids)
            promotion_index = candidate.get("promotion_index")
            if isinstance(promotion_index, int):
                promotion_candidate_ids[promotion_index] = candidate_id
        for promotion in (materialized or {}).get("document_promotions", []):
            promotion_index = promotion.get("promotion_index") if isinstance(promotion, dict) else None
            repository.insert_document_promotion(
                conn,
                document_id,
                promotion,
                candidate_id=promotion_candidate_ids.get(promotion_index) if isinstance(promotion_index, int) else None,
            )
        repository.insert_processing_state(conn, persisted_state)
        repository.insert_document_entities(conn, document_id, build_observed_semantics(prepared.sanitized_segments, graph_relations), evidence_index=evidence_index)
        if materialized is not None:
            repository.insert_document_entities(conn, document_id, materialized, evidence_index=evidence_index)
            repository.insert_materialization_audits(conn, document_id, materialized.get("audits", []))
        insert_fts_entry_fn(
            conn,
            document_id,
            doc,
            prepared.sanitized_fields,
            prepared.sanitized_rows,
            prepared.sanitized_segments,
            prepared.tags,
            prepared.people,
            prepared.orgs,
            promotions=(materialized or {}).get("document_promotions", []),
        )
        repository.log_history(conn, document_id, "loaded", new_hash=content_hash)
        conn.commit()
        return LoadResult(status="archived_and_loaded" if was_archived else "loaded", document_id=document_id)
    except Exception as exc:
        if conn.in_transaction:
            conn.rollback()
        logger.error("Fehler beim Laden von %s: %s", document_id, exc)
        return LoadResult(status="error", document_id=document_id, reason=str(exc))


__all__ = ["load_document"]
