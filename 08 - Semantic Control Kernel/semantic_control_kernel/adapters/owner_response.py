from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.atomic_json import atomic_write_text


def _load_owner_response(path: Path, diagnostics: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not path.exists():
        atomic_write_text(path, "")
        diagnostics.append({"code": "owner_response_missing"})
        return None
    text = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        diagnostics.append({"code": "owner_response_invalid_json", "message": str(exc)})
        return None
    if not isinstance(parsed, dict):
        diagnostics.append({"code": "owner_response_not_object"})
        return None
    if "status" not in parsed and "error" not in parsed:
        diagnostics.append({"code": "owner_response_missing_status"})
        return None
    return parsed


def _owner_status(payload: Mapping[str, Any]) -> str:
    value = payload.get("status")
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"applied"}:
            return "ok"
        return normalized
    if payload.get("error"):
        return "error"
    return "invalid"


def _owner_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in ("schema_version", "status", "owner_module", "owner_action", "message", "error", "reason", "headline"):
        if key in payload:
            summary[key] = payload[key]
    return summary


def _owner_error_summary(payload: Mapping[str, Any]) -> str:
    for key in ("reason", "error", "message", "headline"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _mapping_field(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _derived_target_identity_proof(
    target_proof: Mapping[str, Any],
    output_refs: Mapping[str, Any],
) -> dict[str, Any]:
    derived = dict(target_proof)
    for key in (
        "artifact_root_path",
        "artifact_root_path_hash",
        "database_path",
        "database_path_hash",
        "pipeline_batch_id",
        "merge_run_id",
        "taxonomy_id",
        "taxonomy_fingerprint",
        "projection_id",
        "projection_fingerprint",
        "selection_fingerprint",
        "sample_selection_id",
        "release_id",
        "release_version",
        "release_fingerprint",
    ):
        value = output_refs.get(key)
        if value:
            derived.setdefault(key, value)
    if output_refs.get("fingerprint"):
        derived.setdefault("release_fingerprint", output_refs["fingerprint"])
    database_ref = _mapping_field(output_refs, "database_ref")
    for key in ("database_path", "database_path_hash"):
        value = database_ref.get(key)
        if value:
            derived.setdefault(key, value)
    release_ref = _release_identity_ref(output_refs)
    for key in ("release_id", "release_version", "release_fingerprint"):
        value = release_ref.get(key)
        if value:
            derived.setdefault(key, value)
    semantic_merge_package = _mapping_field(output_refs, "semantic_merge_package")
    for key in ("release_id", "release_version", "release_fingerprint"):
        value = semantic_merge_package.get(key)
        if value:
            derived.setdefault(key, value)
    component_identity = _mapping_field(output_refs, "component_identity")
    for key in ("taxonomy_id", "taxonomy_fingerprint", "projection_id", "projection_fingerprint"):
        value = component_identity.get(key)
        if value:
            derived.setdefault(key, value)
    updated_taxonomy_ref = _mapping_field(output_refs, "updated_taxonomy_ref")
    for key in ("taxonomy_id", "taxonomy_fingerprint"):
        value = updated_taxonomy_ref.get(key)
        if value:
            derived.setdefault(key, value)
    updated_projection_refs = output_refs.get("updated_projection_refs")
    if isinstance(updated_projection_refs, list):
        for item in updated_projection_refs:
            if isinstance(item, Mapping) and item.get("projection_fingerprint"):
                derived.setdefault("projection_fingerprint", item["projection_fingerprint"])
                if item.get("projection_id"):
                    derived.setdefault("projection_id", item["projection_id"])
                break
    return derived


def _release_identity_ref(output_refs: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("release_ref", "updated_release_ref"):
        candidate = _mapping_field(output_refs, key)
        if candidate:
            return candidate
    work_package_ref = _mapping_field(output_refs, "work_package_ref")
    updated_release_ref = _mapping_field(work_package_ref, "updated_release_ref")
    if updated_release_ref:
        return updated_release_ref
    return {}


def _missing_target_proof_fields(target_proof: Mapping[str, Any], required_groups: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for group in required_groups:
        alternatives = tuple(part.strip() for part in group.split("|") if part.strip())
        if alternatives and not any(target_proof.get(part) for part in alternatives):
            missing.append(group)
    return missing


def _target_identity_mismatches(
    requested_identity: Mapping[str, Any],
    proven_identity: Mapping[str, Any],
) -> list[str]:
    ignored_keys = {"created_from", "lock_scope", "schema_version", "state_snapshot_id", "target_hash"}
    mismatches: list[str] = []
    for key, expected_value in requested_identity.items():
        if key in ignored_keys or key not in proven_identity:
            continue
        actual_value = proven_identity.get(key)
        if _normalize_identity_value(actual_value) != _normalize_identity_value(expected_value):
            mismatches.append(key)
    return mismatches


def _normalize_identity_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_identity_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_identity_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_identity_value(item) for item in value)
    return value
