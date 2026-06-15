from __future__ import annotations

from typing import Any

from ..models.serialization import now_iso
from .types import ProjectionMetadata, ReleaseAnalysis


def analyze_release(release: dict[str, Any]) -> ReleaseAnalysis:
    master = release.get("master_taxonomy", {})
    projections = release.get("projections", [])
    warnings: list[str] = []
    issues: list[str] = []
    if len(projections) <= 1:
        warnings.append("Es ist nur eine Projection im Release vorhanden.")
    if not master.get("entity_types"):
        issues.append("Master-Taxonomie enthaelt keine entity_types.")
    if not master.get("promotion_slots"):
        issues.append("Master-Taxonomie enthaelt keine promotion_slots.")
    if all(not projection.get("promotion_rules") for projection in projections if isinstance(projection, dict)):
        issues.append("Keine Projection enthaelt promotion_rules.")
    return {
        "release_id": release.get("release_id"),
        "release_version": release.get("release_version"),
        "projection_count": len(projections),
        "issues": issues,
        "warnings": warnings,
        "generated_at": now_iso(),
    }


def projection_metadata(payload: dict[str, Any]) -> ProjectionMetadata:
    projection = payload.get("projection")
    if isinstance(projection, dict):
        return {
            "projection_id": str(projection.get("projection_id") or "").strip(),
            "projection_family": str(projection.get("projection_family") or ""),
            "master_taxonomy_id": str(projection.get("master_taxonomy_id") or ""),
            "master_taxonomy_version": str(projection.get("master_taxonomy_version") or ""),
            "projection_version": str(projection.get("projection_version") or ""),
            "projection_fingerprint": str(projection.get("projection_fingerprint") or ""),
            "materialization_profile_id": str(projection.get("materialization_profile_id") or ""),
        }
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    profile_id = str(context.get("taxonomy_profile_id", "")).strip()
    return {
        "projection_id": profile_id or "unknown",
        "projection_family": "legacy",
        "master_taxonomy_id": "",
        "master_taxonomy_version": "",
        "projection_version": "legacy",
        "projection_fingerprint": "",
        "materialization_profile_id": "document_entities.v1",
    }
