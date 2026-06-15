from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from semantic_control_kernel.policy.merge_policy import collision_policy, collision_requires_user_choice
from semantic_control_kernel.repository.paths import stable_hash, utc_iso
from semantic_control_kernel.types.merge import DatabaseMergeCollisionManifest
from semantic_control_kernel.validation.merge_validation import (
    collision_manifest_blocks_activation,
    manifest_fingerprint,
    validate_collision_manifest,
)
from semantic_control_kernel.workflows.merge.collision_manifest_reuse import reuse_existing_manifest


def build_collision_entry(
    *,
    collision_id: str,
    collision_class: str,
    source_refs: Sequence[Mapping[str, Any]],
    target_ref: Mapping[str, Any] | None = None,
    selected_resolution: str | None = None,
    diagnostics: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    policy = collision_policy(collision_class)
    requires_choice = collision_requires_user_choice(collision_class, selected_resolution=selected_resolution)
    status = "requires_user_choice" if requires_choice else "resolved"
    return {
        "blocks_activation": requires_choice,
        "collision_class": collision_class,
        "collision_id": collision_id,
        "default_policy": policy.default_policy,
        "diagnostics": [dict(item) for item in diagnostics],
        "requires_user_choice": requires_choice,
        "resolution_owner": "kernel_dialog" if requires_choice else policy.owner_function,
        "resolution_status": status,
        "selected_resolution": selected_resolution or (None if requires_choice else policy.default_policy),
        "source_refs": [dict(item) for item in source_refs],
        "target_ref": dict(target_ref or {}),
    }


def build_collision_manifest(
    *,
    merge_run_id: str,
    merge_route: str,
    source_databases: Sequence[Mapping[str, Any]],
    target_artifact_root: str,
    target_database_path: str,
    collisions: Sequence[Mapping[str, Any]] = (),
    duplicate_policy: str = "keep_both_by_default",
) -> DatabaseMergeCollisionManifest:
    normalized_collisions = [
        canonicalize_owner_collision(item)
        for item in collisions
        if isinstance(item, Mapping)
    ]
    payload = {
        "schema_version": DatabaseMergeCollisionManifest.SCHEMA_VERSION,
        "collisions": normalized_collisions,
        "created_at": utc_iso(),
        "duplicate_policy": duplicate_policy,
        "manifest_fingerprint": "",
        "manifest_revision": 1,
        "merge_route": merge_route,
        "merge_run_id": merge_run_id,
        "resolution_summary": _summary(normalized_collisions),
        "source_databases": [dict(item) for item in source_databases],
        "target_artifact_root": target_artifact_root,
        "target_database_path": target_database_path,
        "updated_at": utc_iso(),
    }
    payload["manifest_fingerprint"] = manifest_fingerprint(payload)
    validate_collision_manifest(payload)
    return DatabaseMergeCollisionManifest(payload)


def canonicalize_owner_collision(collision: Mapping[str, Any]) -> dict[str, Any]:
    """Force owner-reported collisions back through Kernel policy semantics."""

    collision_class = str(collision.get("collision_class", "")).strip()
    collision_id = str(collision.get("collision_id", "")).strip()
    if not collision_class or not collision_id:
        raise ValueError("Owner collision entries require collision_id and collision_class.")
    source_refs = collision.get("source_refs")
    if not isinstance(source_refs, Sequence) or isinstance(source_refs, (str, bytes)):
        raise ValueError("Owner collision entries require source_refs.")
    selected_resolution = _optional_text(collision.get("selected_resolution"))
    entry = build_collision_entry(
        collision_id=collision_id,
        collision_class=collision_class,
        source_refs=[dict(item) for item in source_refs if isinstance(item, Mapping)],
        target_ref=dict(collision.get("target_ref", {})) if isinstance(collision.get("target_ref"), Mapping) else {},
        selected_resolution=selected_resolution,
        diagnostics=[
            dict(item)
            for item in collision.get("diagnostics", [])
            if isinstance(item, Mapping)
        ]
        if isinstance(collision.get("diagnostics"), Sequence) and not isinstance(collision.get("diagnostics"), (str, bytes))
        else (),
    )
    if str(collision.get("resolution_status", "")).strip() == "unresolved":
        entry["resolution_status"] = "unresolved"
        entry["blocks_activation"] = True
    return entry


def append_manifest_revision(
    manifest: Mapping[str, Any],
    *,
    added_collisions: Sequence[Mapping[str, Any]] = (),
    selected_resolutions: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
) -> DatabaseMergeCollisionManifest:
    payload = deepcopy(dict(manifest))
    collisions = [dict(item) for item in payload.get("collisions", []) if isinstance(item, Mapping)]
    resolution_map = _selected_resolution_map(selected_resolutions)
    if resolution_map:
        for collision in collisions:
            cid = str(collision.get("collision_id", ""))
            if cid in resolution_map:
                collision["selected_resolution"] = resolution_map[cid]
                collision["resolution_status"] = "resolved"
                collision["requires_user_choice"] = False
                collision["blocks_activation"] = False
    collisions.extend(dict(item) for item in added_collisions)
    payload["collisions"] = collisions
    payload["manifest_revision"] = int(payload.get("manifest_revision", 0)) + 1
    payload["updated_at"] = utc_iso()
    payload["resolution_summary"] = _summary(collisions)
    payload["manifest_fingerprint"] = ""
    payload["manifest_fingerprint"] = manifest_fingerprint(payload)
    validate_collision_manifest(payload)
    return DatabaseMergeCollisionManifest(payload)


def activation_is_blocked(manifest: Mapping[str, Any]) -> bool:
    validate_collision_manifest(manifest)
    return collision_manifest_blocks_activation(manifest)


def _summary(collisions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(collisions)
    requires_user_choice = sum(1 for item in collisions if item.get("resolution_status") == "requires_user_choice")
    unresolved = sum(1 for item in collisions if item.get("resolution_status") == "unresolved")
    resolved = total - requires_user_choice - unresolved
    return {
        "resolved": resolved,
        "requires_user_choice": requires_user_choice,
        "total": total,
        "unresolved": unresolved,
    }


def collision_id_for(collision_class: str, *parts: object) -> str:
    return f"col_{stable_hash(collision_class + ':' + repr(parts))[:12]}"


def _selected_resolution_map(selected_resolutions: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None) -> dict[str, Any]:
    if selected_resolutions is None:
        return {}
    if isinstance(selected_resolutions, Mapping):
        return {str(key): value for key, value in selected_resolutions.items() if str(key)}
    normalized: dict[str, Any] = {}
    for item in selected_resolutions:
        if not isinstance(item, Mapping):
            continue
        collision_id = str(item.get("collision_id", ""))
        if not collision_id:
            continue
        normalized[collision_id] = item.get("selected_resolution")
    return normalized


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
