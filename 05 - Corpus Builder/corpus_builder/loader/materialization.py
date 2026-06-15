"""Semantic materialization and processing-state helpers for loader workflows."""

from __future__ import annotations

from ..models.serialization import now_iso
from ..semantic_release import materialize_document_semantics, projection_metadata, validate_payload_against_release
from . import audit
from .types import JsonDict


def materialize(
    document_id: str,
    preferred_json: JsonDict,
    normalized_json: JsonDict | None,
    semantic_release: JsonDict | None,
    source_mode: str,
    *,
    validate_release: bool,
) -> tuple[JsonDict, JsonDict | None]:
    projection_meta = projection_metadata(preferred_json)
    if not isinstance(semantic_release, dict) or not isinstance(normalized_json, dict):
        return projection_meta, None
    if validate_release:
        validate_payload_against_release(preferred_json, semantic_release)
    try:
        return projection_meta, materialize_document_semantics(document_id, preferred_json, semantic_release)
    except Exception as exc:
        return projection_meta, audit.fallback_materialization(document_id=document_id, payload=preferred_json, release=semantic_release, reason=str(exc), source_mode=source_mode)


def rematerialized_processing_state(materialized: JsonDict, semantic_release: JsonDict) -> JsonDict:
    state = dict(materialized.get("processing_state", {}))
    state["document_id"] = str(state.get("document_id") or materialized.get("document_id") or "")
    state["materialization_version"] = str(semantic_release.get("materialization_version") or state.get("materialization_version") or "")
    snapshot = semantic_release.get("active_snapshot") if isinstance(semantic_release.get("active_snapshot"), dict) else {}
    state["materialized_snapshot_id"] = str(snapshot.get("snapshot_id") or state.get("materialized_snapshot_id") or "") or None
    state["projection_id"] = str(materialized.get("projection_id") or state.get("projection_id") or "")
    state["projection_fingerprint"] = str(materialized.get("projection_fingerprint") or state.get("projection_fingerprint") or "")
    state["materialization_state"] = str(state.get("materialization_state") or "current")
    state["stale_reason"] = state.get("stale_reason")
    state["last_materialized_at"] = now_iso()
    return state


def persisted_processing_state(
    document_id: str,
    projection_meta: JsonDict,
    materialized: JsonDict | None,
    semantic_release: JsonDict | None,
    source_mode: str,
) -> JsonDict:
    if materialized is not None and isinstance(semantic_release, dict):
        return rematerialized_processing_state(materialized, semantic_release)
    state = dict((materialized or {}).get("processing_state", {}))
    state["document_id"] = document_id
    state["materialization_version"] = str(state.get("materialization_version") or (semantic_release or {}).get("materialization_version") or "")
    snapshot = (semantic_release or {}).get("active_snapshot") if isinstance((semantic_release or {}).get("active_snapshot"), dict) else {}
    state["materialized_snapshot_id"] = str(snapshot.get("snapshot_id") or state.get("materialized_snapshot_id") or "") or None
    state["projection_id"] = str(state.get("projection_id") or (materialized or {}).get("projection_id") or projection_meta.get("projection_id") or "")
    state["projection_fingerprint"] = str(state.get("projection_fingerprint") or (materialized or {}).get("projection_fingerprint") or projection_meta.get("projection_fingerprint") or "")
    state["materialization_state"] = str(state.get("materialization_state") or ("current" if state["projection_id"] else "legacy"))
    state["stale_reason"] = state.get("stale_reason")
    state["source_mode"] = str(state.get("source_mode") or source_mode or "normalized")
    state["last_materialized_at"] = str(state.get("last_materialized_at") or now_iso())
    return state
