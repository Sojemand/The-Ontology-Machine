"""Workflow orchestration for semantic release materialization."""
from __future__ import annotations

from typing import Any

from .domain import materialize_projection
from .materialization_domain import build_materialization_result
from .policy import materialize_promotions
from .types import MaterializationInputs, MaterializedSemantics
from .validation import validate_payload_against_release


def materialize_document_semantics(
    document_id: str,
    payload: dict[str, Any],
    release: dict[str, Any],
) -> MaterializedSemantics:
    projection_meta = validate_payload_against_release(payload, release)
    projection_id = str(projection_meta.get("projection_id") or "").strip()
    projection = materialize_projection(release, projection_id)
    release_fingerprint = str(release.get("fingerprint") or release.get("release_fingerprint") or "")
    materialization_version = str(release.get("materialization_version") or "1")
    slot_candidates, document_promotions = materialize_promotions(
        payload,
        projection,
        release_fingerprint=release_fingerprint,
        materialization_version=materialization_version,
    )
    return build_materialization_result(
        MaterializationInputs(
            document_id=document_id,
            payload=payload,
            projection=projection,
            projection_meta=projection_meta,
            materialization_version=materialization_version,
            release_fingerprint=release_fingerprint,
            active_snapshot_id=_active_snapshot_id(release),
        ),
        slot_candidates,
        document_promotions,
    )


def _active_snapshot_id(release: dict[str, Any]) -> str | None:
    snapshot = release.get("active_snapshot")
    if not isinstance(snapshot, dict):
        return None
    value = str(snapshot.get("snapshot_id") or "").strip()
    return value or None
