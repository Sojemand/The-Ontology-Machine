from __future__ import annotations

import copy
from typing import Any

from ..models.serialization import utc_now_iso
from ..runtime_semantic_assets import build_runtime_semantic_assets
from ..semantic_release import policy as release_policy
from ..semantic_release.shared_identity import build_master_taxonomy_release_id
from ..taxonomy import SEMANTIC_RELEASE_SCHEMA_VERSION, upgrade_master_taxonomy_v2, upgrade_projection_payload_v2
from .taxonomy_release_draft_db import db_update_decision
from .taxonomy_release_draft_schema import RELEASE_REQUIRED_KEYS, verification

_MASTER_TEXT_KEYS = frozenset({"label", "description", "aliases"})
_MASTER_SECTIONS = (
    "domains",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
    "promotion_slots",
    "entity_types",
    "role_types",
    "relation_types",
)


def verify_release(
    release: dict[str, Any],
    *,
    origin: dict[str, Any] | None = None,
    corpus_db_path: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    issues: list[str] = []
    warnings: list[str] = []
    payload = copy.deepcopy(release)
    missing = sorted(RELEASE_REQUIRED_KEYS - set(payload))
    if missing:
        raise ValueError(f"Semantic Release unvollstaendig: {', '.join(missing)}")
    master = _verified_master(payload)
    projections = _verified_projections(payload, master)
    projection_ids = sorted([str(item["projection_id"]) for item in projections], key=lambda item: (item.casefold(), item))
    master_core = master_core_signature(master)
    origin = dict(origin or {})
    original_master_core = str(origin.get("master_core_signature") or "")
    original_master_release_id = str(origin.get("master_taxonomy_release_id") or payload.get("master_taxonomy_release_id") or "")
    if original_master_core and original_master_core == master_core and original_master_release_id:
        master_taxonomy_release_id = original_master_release_id
    else:
        master_taxonomy_release_id = build_master_taxonomy_release_id(_master_core_payload(master))
        if original_master_release_id and master_taxonomy_release_id != original_master_release_id:
            warnings.append("Master taxonomy machine fields changed; current DB may require new materialization.")
    verified = _verified_release_payload(payload, master, projections, projection_ids, master_taxonomy_release_id)
    if not projections:
        issues.append("Release enthaelt keine Projections.")
    status = "verified" if not issues else "blocked"
    return verified, verification(
        status,
        issues=issues,
        warnings=warnings,
        db_decision=db_update_decision(corpus_db_path, verified),
        release_fingerprint=verified["fingerprint"],
        master_taxonomy_release_id=master_taxonomy_release_id,
        projection_count=len(projections),
    )


def master_core_signature(master: dict[str, Any]) -> str:
    return build_master_taxonomy_release_id(_master_core_payload(master))


def _verified_release_payload(
    payload: dict[str, Any],
    master: dict[str, Any],
    projections: list[dict[str, Any]],
    projection_ids: list[str],
    master_taxonomy_release_id: str,
) -> dict[str, Any]:
    verified = {
        "schema_version": str(payload.get("schema_version") or SEMANTIC_RELEASE_SCHEMA_VERSION),
        "release_id": _required_text(payload.get("release_id"), "release_id"),
        "release_version": _required_text(payload.get("release_version"), "release_version"),
        "master_taxonomy_id": str(master.get("taxonomy_id") or payload.get("master_taxonomy_id") or "").strip(),
        "master_taxonomy_version": str(master.get("taxonomy_version") or payload.get("master_taxonomy_version") or "").strip(),
        "master_taxonomy_release_id": master_taxonomy_release_id,
        "runtime_locale": str(payload.get("runtime_locale") or "").strip() or None,
        "projection_ids": projection_ids,
        "materialization_version": str(payload.get("materialization_version") or "1"),
        "created_at": str(payload.get("created_at") or utc_now_iso()),
        "fingerprint": "",
        "master_taxonomy": master,
        "projections": projections,
        "analysis": release_policy.analyze_taxonomy_shape(master, projections),
    }
    verified["fingerprint"] = release_policy.build_release_fingerprint(verified)
    verified["release_fingerprint"] = verified["fingerprint"]
    runtime_assets = build_runtime_semantic_assets(verified).to_dict()
    verified["projection_catalog"] = runtime_assets["projection_catalog"]
    verified["runtime_semantic_assets"] = runtime_assets
    return verified


def _verified_master(payload: dict[str, Any]) -> dict[str, Any]:
    master = dict(payload.get("master_taxonomy") or {})
    if not master.get("taxonomy_id"):
        master["taxonomy_id"] = str(payload.get("master_taxonomy_id") or "").strip()
    if not master.get("taxonomy_version"):
        master["taxonomy_version"] = str(payload.get("master_taxonomy_version") or "").strip()
    return upgrade_master_taxonomy_v2(master, include_semantic_defaults=False)


def _verified_projections(payload: dict[str, Any], master: dict[str, Any]) -> list[dict[str, Any]]:
    projections = payload.get("projections")
    if not isinstance(projections, list):
        raise ValueError("projections muss eine Liste sein.")
    verified: list[dict[str, Any]] = []
    for index, projection in enumerate(projections):
        if not isinstance(projection, dict):
            raise ValueError(f"projections[{index}] muss ein JSON-Objekt sein.")
        current = copy.deepcopy(projection)
        current["master_taxonomy_id"] = str(master.get("taxonomy_id") or "")
        current["master_taxonomy_version"] = str(master.get("taxonomy_version") or "")
        verified.append(upgrade_projection_payload_v2(master, current))
    return sorted(verified, key=lambda item: (str(item["projection_id"]).casefold(), str(item["projection_id"])))


def _master_core_payload(master: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: _strip_text_fields(value)
        for key, value in master.items()
        if key not in _MASTER_TEXT_KEYS and key != "projection_templates"
    }
    for section in _MASTER_SECTIONS:
        if section in master:
            payload[section] = _strip_text_fields(master[section])
    return payload


def _strip_text_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _strip_text_fields(child) for key, child in value.items() if str(key) not in _MASTER_TEXT_KEYS}
    if isinstance(value, list):
        return [_strip_text_fields(item) for item in value]
    return value


def _required_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return text
