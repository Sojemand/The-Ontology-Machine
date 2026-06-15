from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.policy.merge_policy import activation_blocking_collisions, collision_policy, collision_requires_user_choice
from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.merge import MERGE_COLLISION_REQUIRED_FIELDS
from semantic_control_kernel.validation.merge_validation_common import require_fields, stable_payload


def validate_collision_manifest(manifest: Mapping[str, Any]) -> None:
    require_fields(
        manifest,
        (
            "schema_version",
            "merge_run_id",
            "merge_route",
            "created_at",
            "updated_at",
            "source_databases",
            "target_artifact_root",
            "target_database_path",
            "duplicate_policy",
            "collisions",
            "resolution_summary",
            "manifest_revision",
            "manifest_fingerprint",
        ),
        "kernel.database_merge_collision_manifest.v1",
    )
    collisions = manifest.get("collisions")
    if not isinstance(collisions, list):
        raise ValueError("collisions must be a list.")
    for collision in collisions:
        if not isinstance(collision, Mapping):
            raise ValueError("collision entries must be objects.")
        require_fields(collision, MERGE_COLLISION_REQUIRED_FIELDS, "kernel.database_merge_collision_manifest.v1.collisions[]")
        _validate_collision_entry_semantics(collision)
    if manifest.get("manifest_fingerprint") != manifest_fingerprint(manifest):
        raise ValueError("manifest_fingerprint does not match collision manifest.")


def collision_manifest_blocks_activation(manifest: Mapping[str, Any]) -> bool:
    collisions = [item for item in manifest.get("collisions", []) if isinstance(item, Mapping)]
    return bool(activation_blocking_collisions(collisions))


def manifest_fingerprint(manifest: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_fingerprint"}
    return stable_hash(repr(stable_payload(payload)))


def _validate_collision_entry_semantics(collision: Mapping[str, Any]) -> None:
    collision_class = str(collision.get("collision_class", "")).strip()
    policy = collision_policy(collision_class)
    if str(collision.get("default_policy", "")) != policy.default_policy:
        raise ValueError(f"{collision_class} default_policy does not match Phase 12 collision policy.")
    status = str(collision.get("resolution_status", "")).strip()
    if status not in {"resolved", "requires_user_choice", "unresolved"}:
        raise ValueError("resolution_status must be resolved, requires_user_choice or unresolved.")
    if status == "requires_user_choice":
        _validate_user_choice_collision(collision)
        return
    if status == "unresolved":
        if not bool(collision.get("blocks_activation")):
            raise ValueError("unresolved collisions must block activation.")
        return
    _validate_resolved_collision(collision_class, collision)


def _validate_user_choice_collision(collision: Mapping[str, Any]) -> None:
    if not bool(collision.get("requires_user_choice")):
        raise ValueError("requires_user_choice collisions must carry requires_user_choice=true.")
    if not bool(collision.get("blocks_activation")):
        raise ValueError("requires_user_choice collisions must block activation.")
    if str(collision.get("resolution_owner", "")) != "kernel_dialog":
        raise ValueError("requires_user_choice collisions must be owned by the Kernel dialog.")


def _validate_resolved_collision(collision_class: str, collision: Mapping[str, Any]) -> None:
    if bool(collision.get("requires_user_choice")):
        raise ValueError("resolved collisions must not carry requires_user_choice=true.")
    if bool(collision.get("blocks_activation")):
        raise ValueError("resolved collisions must not block activation.")
    selected_resolution = str(collision.get("selected_resolution") or "").strip()
    if collision_requires_user_choice(collision_class, selected_resolution=None) and not selected_resolution:
        raise ValueError(f"{collision_class} cannot be resolved without a Kernel selected_resolution.")
