"""Activation confirmation artifact validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIRMATION_ARTIFACT_VERSION = "semantic_activation_confirmation_v1"


def validate_activation_confirmation(
    *,
    artifact_path: str | Path | None,
    preflight: dict[str, Any],
    corpus_db_path: str | Path,
) -> str:
    if not bool(preflight.get("requires_confirmation")):
        return "activate_only"
    if artifact_path is None:
        raise ValueError("activation_confirmation_missing")
    resolved_path = Path(artifact_path)
    if not resolved_path.exists():
        raise ValueError(f"Aktivierungsbestaetigung fehlt: {resolved_path}")
    payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Aktivierungsbestaetigung muss ein JSON-Objekt sein.")
    if str(payload.get("artifact_version") or "").strip() != CONFIRMATION_ARTIFACT_VERSION:
        raise ValueError("Aktivierungsbestaetigung hat eine ungueltige artifact_version.")
    expected = preflight.get("confirmation_artifact_template")
    if not isinstance(expected, dict):
        raise ValueError("Aktivierungs-Preflight ist unvollstaendig.")
    _assert_confirmation_matches(payload, expected, corpus_db_path)
    decision = str(payload.get("decision") or "").strip()
    if decision not in {"activate_only", "activate_and_backfill"}:
        raise ValueError("Aktivierungsbestaetigung enthaelt eine ungueltige decision.")
    return decision


def _assert_confirmation_matches(
    payload: dict[str, Any],
    expected: dict[str, Any],
    corpus_db_path: str | Path,
) -> None:
    comparisons = (
        ("corpus_db_path", str(corpus_db_path)),
        ("release_path", str(expected["release_path"])),
        ("expected_current_snapshot_id", expected.get("expected_current_snapshot_id")),
        ("expected_new_snapshot_id", expected.get("expected_new_snapshot_id")),
        ("expected_release_fingerprint", expected.get("expected_release_fingerprint")),
        ("expected_master_taxonomy_release_id", expected.get("expected_master_taxonomy_release_id")),
        ("expected_runtime_locale", expected.get("expected_runtime_locale")),
    )
    for key, expected_value in comparisons:
        if payload.get(key) != expected_value:
            raise ValueError(f"Aktivierungsbestaetigung passt nicht zum Preflight: {key}")
