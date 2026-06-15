"""Snapshot identity and envelope helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .snapshot_validation import validate_embedded_release_bundle
from .types import ActiveSnapshotEnvelope
from .validation import validate_release_payload

_SNAPSHOT_VOLATILE_FIELDS = frozenset({"active_snapshot", "created_at", "release_path", "snapshot_id"})


def resolve_runtime_locale(release: dict[str, Any]) -> tuple[str, str]:
    return _require_text(release.get("runtime_locale"), "release.runtime_locale"), "release.runtime_locale"


def build_snapshot_id(release: dict[str, Any]) -> str:
    embedded_release, _projection_catalog, _runtime_assets = _embedded_release_payload(release)
    normalized = _snapshot_identity_payload(embedded_release)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def build_snapshot_envelope(
    release: dict[str, Any],
    *,
    release_path: str,
    snapshot_id: str | None = None,
) -> ActiveSnapshotEnvelope:
    validate_release_payload(release)
    embedded_release, projection_catalog, runtime_assets = _embedded_release_payload(release)
    resolved_snapshot_id = snapshot_id or build_snapshot_id(embedded_release)
    runtime_locale, _provenance = resolve_runtime_locale(embedded_release)
    return {
        "snapshot_id": resolved_snapshot_id,
        "release": _release_with_active_snapshot(embedded_release, resolved_snapshot_id, release_path),
        "projection_catalog": projection_catalog,
        "runtime_semantic_assets": runtime_assets,
        "master_taxonomy_release_id": _require_text(
            embedded_release.get("master_taxonomy_release_id"),
            "release.master_taxonomy_release_id",
        ),
        "runtime_locale": runtime_locale,
        "release_path": str(release_path),
    }


def recommended_confirmation_filename(release: dict[str, Any], *, snapshot_id: str) -> str:
    release_id = str(release.get("release_id") or "").strip() or "semantic-release"
    return f"{release_id}.{snapshot_id[:16]}.activation_confirmation.json"


def release_without_active_snapshot(release: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(release))
    payload.pop("active_snapshot", None)
    return payload


def _release_with_active_snapshot(
    release: dict[str, Any],
    snapshot_id: str,
    release_path: str,
) -> dict[str, Any]:
    payload = json.loads(json.dumps(release))
    payload["active_snapshot"] = {
        "snapshot_id": snapshot_id,
        "release_path": str(release_path),
    }
    return payload


def _embedded_release_payload(release: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = json.loads(json.dumps(release))
    projection_catalog = payload.get("projection_catalog")
    runtime_assets = payload.get("runtime_semantic_assets")
    if projection_catalog is None or runtime_assets is None:
        raise ValueError(
            "Semantic Release Bundle ist inkonsistent: "
            "projection_catalog und runtime_semantic_assets muessen gemeinsam vorliegen."
        )
    validated_projection_catalog, validated_runtime_assets = validate_embedded_release_bundle(payload)
    payload["projection_catalog"] = validated_projection_catalog
    payload["runtime_semantic_assets"] = validated_runtime_assets
    return payload, validated_projection_catalog, validated_runtime_assets


def _snapshot_identity_payload(release: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(release))
    for field_name in _SNAPSHOT_VOLATILE_FIELDS:
        payload.pop(field_name, None)
    return payload


def _require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return text
