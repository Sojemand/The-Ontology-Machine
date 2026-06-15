from __future__ import annotations

from typing import Any

from semantic_control_kernel.repository._helpers import target_identity_hash, target_identity_scope
from semantic_control_kernel.repository.errors import StateRepositoryError
from semantic_control_kernel.repository.lock_store_constants import LOCK_TYPE_REQUIRED_LIVENESS


def normalize_liveness_evidence(
    lock_type: str,
    target_identity: dict[str, Any],
    owner_workflow_run_id: str,
    liveness_evidence: dict[str, Any],
    *,
    heartbeat_at: str,
) -> dict[str, Any]:
    evidence = dict(liveness_evidence)
    evidence.setdefault("workflow_run_id", owner_workflow_run_id)
    evidence.setdefault("heartbeat_at", heartbeat_at)
    for field_name in (
        "database_path_hash",
        "artifact_root_path_hash",
        "release_fingerprint",
        "merge_run_id",
        "target_database_hash",
        "pipeline_batch_id",
        "selection_hash",
    ):
        if field_name not in evidence and field_name in target_identity:
            evidence[field_name] = target_identity[field_name]
    missing = [field_name for field_name in LOCK_TYPE_REQUIRED_LIVENESS.get(lock_type, ()) if not evidence.get(field_name)]
    if missing:
        raise StateRepositoryError(f"{lock_type} lock liveness evidence missing required field(s): {', '.join(missing)}")
    return evidence


def conflict_key(
    lock_type: str,
    target_identity: dict[str, Any],
    owner_workflow_run_id: str,
    liveness_evidence: dict[str, Any],
) -> tuple[str, ...]:
    evidence = dict(liveness_evidence)

    def key_field(field_name: str) -> str:
        return str(evidence.get(field_name) or target_identity.get(field_name) or "")

    def lock_target_field(field_name: str) -> str:
        return key_field(field_name) or str(target_identity.get("target_hash") or "")

    if lock_type == "active_run":
        return (lock_type, owner_workflow_run_id)
    if lock_type == "workspace":
        return (lock_type, lock_target_field("artifact_root_path_hash"))
    if lock_type == "database":
        return (lock_type, lock_target_field("database_path_hash"))
    if lock_type == "release_attach_activation":
        return (lock_type, lock_target_field("database_path_hash"), key_field("release_fingerprint"))
    if lock_type == "merge":
        return (lock_type, key_field("merge_run_id"))
    if lock_type == "rebuild_overwrite":
        return (lock_type, key_field("target_database_hash"))
    return (lock_type, conflict_target_key(target_identity))


def conflict_target_key(target_identity: dict[str, Any]) -> str:
    return f"{target_identity_scope(target_identity)}:{target_identity_hash(target_identity)}"
