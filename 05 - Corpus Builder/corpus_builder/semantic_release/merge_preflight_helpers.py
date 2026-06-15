"""Small pure helpers for merge preflight payloads."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from .merge_constants import (
    COLLISION_ARCHIVE_EXISTING,
    COLLISION_OVERWRITE_EXISTING,
    COLLISION_RESOLUTION_VERSION,
    SNAPSHOT_RISK_CONFIRMATION_VERSION,
    SNAPSHOT_RISK_WARNING,
)

_RECOMMENDED_FILENAME_STEM_LIMIT = 48


def row_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def classify_snapshot_status(active_snapshot_id: str, snapshot: dict[str, Any] | None, reason: str) -> str:
    if snapshot is not None:
        return "ok"
    if not active_snapshot_id:
        return "missing_active_snapshot"
    if "Aktiver Semantic Snapshot fehlt:" in reason:
        return "dangling_active_snapshot_id"
    if "release_json ist ungueltig" in reason or "release_json muss ein JSON-Objekt sein" in reason:
        return "invalid_release_json"
    if "inkonsistent" in reason or "passt nicht zum Semantic Release" in reason:
        return "inconsistent_embedded_snapshot"
    return "snapshot_error"


def allow_with_stale_reasons(source_state: dict[str, Any], target_state: dict[str, Any]) -> list[str]:
    source_release = _snapshot_release(source_state)
    target_release = _snapshot_release(target_state)
    if not source_release or not target_release:
        return []
    reasons: list[str] = []
    if str(source_release.get("fingerprint") or "") != str(target_release.get("fingerprint") or ""):
        reasons.append("release_fingerprint")
    source_snapshot = source_state.get("active_snapshot") or {}
    target_snapshot = target_state.get("active_snapshot") or {}
    if str(source_snapshot.get("runtime_locale") or "") != str(target_snapshot.get("runtime_locale") or ""):
        reasons.append("runtime_locale")
    if _projection_ids(source_release) != _projection_ids(target_release):
        reasons.append("projection_set")
    if _projection_fingerprints(source_release) != _projection_fingerprints(target_release):
        reasons.append("projection_fingerprint")
    if _projection_core_fingerprints(source_release) != _projection_core_fingerprints(target_release):
        reasons.append("projection_core_fingerprint")
    return reasons


def pending_interactions(
    *,
    snapshot_risk: bool,
    collisions: list[str],
    collision_fingerprint: str,
    source_path: Path,
    target_path: Path,
    source_master: str,
    source_state: dict[str, Any],
    target_state: dict[str, Any],
    collision_allowed: bool,
) -> list[dict[str, Any]]:
    interactions: list[dict[str, Any]] = []
    if snapshot_risk:
        interactions.append(_snapshot_risk_interaction(source_path, target_path, source_master, source_state, target_state))
    if collisions and collision_allowed:
        interactions.append(_collision_interaction(source_path, target_path, source_master, collisions, collision_fingerprint))
    return interactions


def _snapshot_risk_interaction(
    source_path: Path,
    target_path: Path,
    source_master: str,
    source_state: dict[str, Any],
    target_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "snapshot_risk_confirmation",
        "headline": SNAPSHOT_RISK_WARNING,
        "summary_lines": [
            "Die semantische Provenance ist danach nicht voll verlaesslich.",
            "Stale-Markierungen und Rematerialisierungsbasis koennen ungenau sein.",
            "Bestehende Daten im Ziel werden nicht geloescht.",
            "Der aktive Ziel-Snapshot bleibt unveraendert.",
        ],
        "choices": [
            {"choice_id": "cancel_merge", "label": "Nein, Merge abbrechen", "decision": None},
            {"choice_id": "confirm_snapshot_risk", "label": "Ja, trotzdem mergen", "decision": "merge_anyway"},
        ],
        "artifact_argument_name": "snapshot_risk_confirmation_artifact_path",
        "artifact_template": {
            "artifact_version": SNAPSHOT_RISK_CONFIRMATION_VERSION,
            "source_db_path": str(source_path),
            "target_db_path": str(target_path),
            "expected_master_taxonomy_release_id": source_master,
            "expected_source_snapshot_status": _snapshot_status_token(source_state),
            "expected_target_snapshot_status": _snapshot_status_token(target_state),
            "decision": "merge_anyway",
        },
        "recommended_filename": _recommended_artifact_filename("snapshot-risk", source_path, target_path),
    }


def _collision_interaction(
    source_path: Path,
    target_path: Path,
    source_master: str,
    collisions: list[str],
    collision_fingerprint: str,
) -> dict[str, Any]:
    return {
        "kind": "collision_resolution",
        "headline": "Achtung, gleiche Dokumente erkannt. Wie soll verfahren werden?",
        "summary_lines": [
            f"Kollisionen: {len(collisions)} Dokumente mit gleicher document_id.",
            "Duplikate im Ziel archivieren behaelt die alte Zielversion als Archivkopie und importiert die Quelle unter der originalen ID.",
            "Bestehende Dokumente ueberschreiben ersetzt die Zielversion unter derselben ID.",
        ],
        "choices": [
            {"choice_id": COLLISION_ARCHIVE_EXISTING, "label": "Duplikate im Ziel archivieren", "decision": COLLISION_ARCHIVE_EXISTING},
            {"choice_id": COLLISION_OVERWRITE_EXISTING, "label": "Bestehende Dokumente ueberschreiben", "decision": COLLISION_OVERWRITE_EXISTING},
        ],
        "artifact_argument_name": "collision_resolution_artifact_path",
        "artifact_template": {
            "artifact_version": COLLISION_RESOLUTION_VERSION,
            "source_db_path": str(source_path),
            "target_db_path": str(target_path),
            "expected_master_taxonomy_release_id": source_master,
            "expected_collision_count": len(collisions),
            "expected_collision_fingerprint": collision_fingerprint,
            "decision": COLLISION_ARCHIVE_EXISTING,
        },
        "recommended_filename": _recommended_artifact_filename("collision-resolution", source_path, target_path),
        "collision_document_ids": collisions[:25],
        "collision_count": len(collisions),
    }


def _snapshot_release(state: dict[str, Any]) -> dict[str, Any]:
    snapshot = state.get("active_snapshot") if isinstance(state.get("active_snapshot"), dict) else {}
    release = snapshot.get("release") if isinstance(snapshot.get("release"), dict) else {}
    return release


def _projection_ids(release: dict[str, Any]) -> list[str]:
    return sorted(str(item).strip() for item in release.get("projection_ids", []) or [] if str(item).strip())


def _projection_fingerprints(release: dict[str, Any], key: str = "projection_fingerprint") -> dict[str, str]:
    projections = release.get("projections")
    if not isinstance(projections, list):
        return {}
    result = {}
    for item in projections:
        if isinstance(item, dict) and item.get("projection_id") and item.get(key):
            result[str(item["projection_id"]).strip()] = str(item[key]).strip()
    return result


def _projection_core_fingerprints(release: dict[str, Any]) -> dict[str, str]:
    return _projection_fingerprints(release, "projection_core_fingerprint")


def _snapshot_status_token(state: dict[str, Any]) -> dict[str, Any]:
    return {"status": state.get("snapshot_status"), "active_snapshot_id": state.get("active_snapshot_id"), "reason": state.get("snapshot_reason")}


def _recommended_artifact_filename(kind: str, source_path: Path, target_path: Path) -> str:
    return f"{_safe_stem(source_path)}.to.{_safe_stem(target_path)}.{kind}.json"


def _safe_stem(path: Path) -> str:
    cleaned = path.stem.replace(" ", "_").replace("/", ".").replace("\\", ".").strip("._-")
    cleaned = cleaned or "corpus"
    if len(cleaned) <= _RECOMMENDED_FILENAME_STEM_LIMIT:
        return cleaned
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:8]
    prefix_length = _RECOMMENDED_FILENAME_STEM_LIMIT - len(digest) - 1
    prefix = cleaned[:prefix_length].rstrip("._-") or "corpus"
    return f"{prefix[:prefix_length]}-{digest}"
