"""Confirmation artifact validation for corpus merges."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .merge_constants import (
    COLLISION_ARCHIVE_EXISTING,
    COLLISION_OVERWRITE_EXISTING,
    COLLISION_RESOLUTION_VERSION,
    SNAPSHOT_RISK_CONFIRMATION_VERSION,
)


def validate_snapshot_risk_confirmation(
    *,
    artifact_path: str | Path | None,
    preflight: dict[str, Any],
) -> str:
    if not bool(preflight.get("snapshot_risk_confirmation_required")):
        return "not_required"
    if artifact_path is None:
        raise ValueError("snapshot_risk_not_confirmed")
    payload = _load_confirmation_payload(artifact_path, expected_version=SNAPSHOT_RISK_CONFIRMATION_VERSION)
    expected = dict(_find_interaction(preflight, kind="snapshot_risk_confirmation").get("artifact_template") or {})
    for key in (
        "source_db_path",
        "target_db_path",
        "expected_master_taxonomy_release_id",
        "expected_source_snapshot_status",
        "expected_target_snapshot_status",
    ):
        if payload.get(key) != expected.get(key):
            raise ValueError(f"Snapshot-Risk-Bestaetigung passt nicht zum Merge-Preflight: {key}")
    decision = str(payload.get("decision") or "").strip()
    if decision != "merge_anyway":
        raise ValueError("Snapshot-Risk-Bestaetigung enthaelt eine ungueltige decision.")
    return decision


def validate_collision_resolution(
    *,
    artifact_path: str | Path | None,
    preflight: dict[str, Any],
) -> str:
    if not bool(preflight.get("collision_resolution_required")):
        return ""
    if artifact_path is None:
        raise ValueError("merge_collision_resolution_missing")
    payload = _load_confirmation_payload(artifact_path, expected_version=COLLISION_RESOLUTION_VERSION)
    expected = dict(_find_interaction(preflight, kind="collision_resolution").get("artifact_template") or {})
    for key in (
        "source_db_path",
        "target_db_path",
        "expected_master_taxonomy_release_id",
        "expected_collision_count",
        "expected_collision_fingerprint",
    ):
        if payload.get(key) != expected.get(key):
            raise ValueError(f"Kollisions-Bestaetigung passt nicht zum Merge-Preflight: {key}")
    decision = str(payload.get("decision") or "").strip()
    if decision not in {COLLISION_ARCHIVE_EXISTING, COLLISION_OVERWRITE_EXISTING}:
        raise ValueError("Kollisions-Bestaetigung enthaelt eine ungueltige decision.")
    return decision


def _find_interaction(preflight: dict[str, Any], *, kind: str) -> dict[str, Any]:
    for item in preflight.get("pending_interactions", []) or []:
        if isinstance(item, dict) and str(item.get("kind") or "") == kind:
            return item
    raise ValueError(f"Merge-Preflight enthaelt keine Interaction fuer {kind}.")


def _load_confirmation_payload(path: str | Path, *, expected_version: str) -> dict[str, Any]:
    resolved_path = Path(path)
    if not resolved_path.exists():
        raise ValueError(f"Bestaetigungsartefakt fehlt: {resolved_path}")
    payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Bestaetigungsartefakt muss ein JSON-Objekt sein.")
    if str(payload.get("artifact_version") or "").strip() != expected_version:
        raise ValueError("Bestaetigungsartefakt hat eine ungueltige artifact_version.")
    return payload


__all__ = ["validate_collision_resolution", "validate_snapshot_risk_confirmation"]
