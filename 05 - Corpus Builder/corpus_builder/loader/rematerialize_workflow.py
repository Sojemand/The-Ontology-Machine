"""Rematerialization workflow for existing corpus documents."""

from __future__ import annotations

import json
import logging
import sqlite3

from ..database import get_fields_dict, get_orgs_list, get_people_list, get_rows_list, get_tags_list
from ..models.results import LoadResult
from ..models.serialization import now_iso
from . import policy, repository
from .candidate_links import link_candidate_evidence
from .materialization import materialize, rematerialized_processing_state
from .preparation import prepare_rematerialize_bundle, select_candidate_payload
from .types import JsonDict

logger = logging.getLogger(__name__)


def rematerialize_document(conn: sqlite3.Connection, document_id: str, semantic_release: JsonDict) -> LoadResult:
    try:
        payload_row = conn.execute("SELECT structured_json, normalized_json FROM document_payloads WHERE document_id = ?", (document_id,)).fetchone()
        if payload_row is None:
            return LoadResult(status="error", document_id=document_id, reason="document_payload fehlt")
        structured_json = json.loads(payload_row["structured_json"]) if payload_row["structured_json"] else {}
        normalized_json = json.loads(payload_row["normalized_json"]) if payload_row["normalized_json"] else None
        structured_json = structured_json if isinstance(structured_json, dict) else {}
        normalized_json = normalized_json if isinstance(normalized_json, dict) else None
        prepared = prepare_rematerialize_bundle(structured_json, normalized_json)
        _projection_meta, materialized = materialize(document_id, prepared.preferred_json, normalized_json, semantic_release, prepared.source_mode, validate_release=False)
        assert materialized is not None
        conn.execute("BEGIN IMMEDIATE")
        repository.clear_semantic_materialization(conn, document_id)
        _touch_document(conn, document_id)
        _update_payload_release(conn, document_id, semantic_release, prepared.preferred_json)
        evidence_index = _insert_rematerialized_candidates(conn, document_id, prepared, materialized)
        repository.insert_processing_state(conn, rematerialized_processing_state(materialized, semantic_release))
        repository.insert_document_entities(conn, document_id, materialized, evidence_index=evidence_index)
        repository.insert_materialization_audits(conn, document_id, materialized.get("audits", []))
        _refresh_fts_entry(conn, document_id, materialized)
        conn.commit()
        return LoadResult(status="loaded", document_id=document_id)
    except Exception as exc:
        if conn.in_transaction:
            conn.rollback()
        logger.error("Fehler bei der Rematerialisierung von %s: %s", document_id, exc)
        return LoadResult(status="error", document_id=document_id, reason=str(exc))


def _touch_document(conn: sqlite3.Connection, document_id: str) -> None:
    conn.execute("UPDATE documents SET updated_at = ? WHERE id = ?", (now_iso(), document_id))


def _update_payload_release(conn: sqlite3.Connection, document_id: str, semantic_release: JsonDict, preferred_json: JsonDict) -> None:
    projection = preferred_json.get("projection")
    conn.execute(
        "UPDATE document_payloads SET release_fingerprint = ?, projection_json = ? WHERE document_id = ?",
        (
            str(semantic_release.get("fingerprint") or ""),
            json.dumps(projection, ensure_ascii=False) if isinstance(projection, dict) else None,
            document_id,
        ),
    )


def _insert_rematerialized_candidates(conn: sqlite3.Connection, document_id: str, prepared, materialized: JsonDict) -> JsonDict:
    evidence_index = repository.build_semantic_evidence_index(conn, document_id)
    path_atom_ids = evidence_index["paths"]
    source_ref_atom_ids = evidence_index["source_refs"]
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    doc_map = dict(row) if row is not None else {}
    payload = select_candidate_payload(prepared.preferred_json, prepared.structured_payload)
    candidates = policy.build_slot_candidates(
        payload,
        doc_map,
        prepared.sanitized_fields,
        prepared.sanitized_rows,
        prepared.tags,
        prepared.people,
        prepared.orgs,
        seed_candidates=materialized.get("slot_candidates"),
    )
    promotion_candidate_ids: dict[int, int] = {}
    for candidate in candidates:
        candidate_id = repository.insert_slot_candidate(conn, document_id, candidate)
        link_candidate_evidence(conn, candidate_id, candidate, path_atom_ids, source_ref_atom_ids)
        promotion_index = candidate.get("promotion_index")
        if isinstance(promotion_index, int):
            promotion_candidate_ids[promotion_index] = candidate_id
    for promotion in materialized.get("document_promotions", []) or []:
        promotion_index = promotion.get("promotion_index") if isinstance(promotion, dict) else None
        repository.insert_document_promotion(
            conn,
            document_id,
            promotion,
            candidate_id=promotion_candidate_ids.get(promotion_index) if isinstance(promotion_index, int) else None,
        )
    return evidence_index


def _refresh_fts_entry(conn: sqlite3.Connection, document_id: str, materialized: JsonDict) -> None:
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        return
    repository.remove_from_fts(conn, document_id)
    repository.insert_fts_entry(
        conn,
        document_id,
        dict(row),
        get_fields_dict(conn, document_id),
        get_rows_list(conn, document_id),
        [],
        get_tags_list(conn, document_id),
        get_people_list(conn, document_id),
        get_orgs_list(conn, document_id),
        promotions=materialized.get("document_promotions", []),
    )
