from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.evidence import evidence_by_kind, first_evidence
from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, TargetIdentity, TargetSelector
from semantic_control_kernel.domain.state_machine.resolver_support import (
    blocker_payload,
    has_blocker,
    materialization_count,
    owner_evidence_matches,
    parse_time,
    record_count,
)
from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.lock_store import LockStore
from semantic_control_kernel.types.enums import DatabaseEmptiness


def resolve_locks(
    lock_store: LockStore | None,
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
    now_utc: datetime,
    blocking: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    lock_payloads: list[dict[str, Any]] = []
    if lock_store is not None:
        try:
            lock_payloads.extend(lock.to_dict() for lock in lock_store.list_active_locks(target_identity.to_dict()))
        except ResumeStateNotFoundError:
            pass
    lock_payloads.extend(ref.payload_ref for ref in evidence_by_kind(bundle, "lock_state", target_identity=target_identity))
    for payload in lock_payloads:
        status = str(payload.get("status", "active"))
        expires_at = parse_time(payload.get("expiry_policy", {}).get("expires_at"))
        if expires_at is not None and expires_at <= now_utc:
            status = "expired"
        ref = {
            "lock_id": payload.get("lock_id", "lock_unknown"),
            "lock_type": payload.get("lock_type", "active_run"),
            "status": status,
            "target_identity": deepcopy(payload.get("target_identity", target_identity.to_dict())),
        }
        refs.append(ref)
        if status == "expired":
            blocking.append(blocker_payload("expired_lock_requires_recovery", target_identity, "", "expired lock", ()))
        elif status in {"active", "pending_resume"}:
            blocking.append(blocker_payload("active_run_lock_conflict", target_identity, "", status, ()))
    return refs


def resolve_artifact_tree(
    selector: TargetSelector,
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
    binding: Mapping[str, Any] | None,
    blocking: list[dict[str, Any]],
) -> dict[str, Any]:
    selector_payload = selector.to_dict()
    artifact_path = (binding or {}).get("artifact_root_path") or selector_payload.get("artifact_root_path")
    folder_evidence = first_evidence(bundle, kind="artifact_tree_folder_contract", target_identity=target_identity)
    exists = bool(artifact_path)
    folder_contract_version = None
    if folder_evidence is not None:
        payload = folder_evidence.payload_ref
        folder_contract_version = payload.get("folder_contract_version")
        if "exists" in payload:
            exists = bool(payload["exists"])
        if payload.get("artifact_root_path") and artifact_path and payload["artifact_root_path"] != artifact_path:
            blocking.append(
                blocker_payload(
                    "binding_conflict",
                    target_identity,
                    "artifact tree path",
                    "filesystem evidence disagrees with Kernel binding",
                    (folder_evidence.evidence_ref_id,),
                )
            )
    if artifact_path and not exists:
        blocking.append(blocker_payload("missing_artifact_tree", target_identity, "artifact tree", "missing", ()))
    return {
        "artifact_root_path": artifact_path,
        "artifact_root_path_hash": target_identity.artifact_root_path_hash,
        "exists": exists,
        "folder_contract_version": folder_contract_version or "artifact_tree.v1",
        "target_identity": target_identity.to_dict(),
    }


def resolve_database(
    selector: TargetSelector,
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
    binding: Mapping[str, Any] | None,
    blocking: list[dict[str, Any]],
) -> dict[str, Any]:
    selector_payload = selector.to_dict()
    database_path = (binding or {}).get("database_path") or selector_payload.get("database_path")
    database_id = (binding or {}).get("database_id") or target_identity.database_id
    summary = first_evidence(bundle, kind="database_content_summary")
    exists = bool(database_path)
    if summary is not None:
        if not owner_evidence_matches(summary.payload_ref, target_identity):
            blocking.append(
                blocker_payload(
                    "owner_evidence_conflict",
                    target_identity,
                    "database owner evidence target",
                    "owner evidence does not match target identity",
                    (summary.evidence_ref_id,),
                )
            )
        if "database_exists" in summary.payload_ref:
            exists = bool(summary.payload_ref["database_exists"])
        elif "exists" in summary.payload_ref:
            exists = bool(summary.payload_ref["exists"])
    if selector_payload.get("selected_existing_database") and not exists:
        blocking.append(blocker_payload("database_missing", target_identity, "existing database", "missing", ()))
    return {
        "database_path": database_path,
        "database_id": database_id,
        "database_path_hash": target_identity.database_path_hash,
        "database_exists": exists,
        "target_identity": target_identity.to_dict(),
    }


def resolve_database_emptiness(
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
    active_database: Mapping[str, Any],
    blocking: list[dict[str, Any]],
) -> str:
    if not active_database.get("database_exists"):
        return DatabaseEmptiness.UNKNOWN.value
    summary = first_evidence(bundle, kind="database_content_summary")
    if summary is not None and not owner_evidence_matches(summary.payload_ref, target_identity):
        if not has_blocker(blocking, "owner_evidence_conflict"):
            blocking.append(
                blocker_payload(
                    "owner_evidence_conflict",
                    target_identity,
                    "database owner evidence target",
                    "owner evidence does not match target identity",
                    (summary.evidence_ref_id,),
                )
            )
        return DatabaseEmptiness.UNKNOWN.value
    current_count = record_count(summary.payload_ref if summary else {})
    batch_counts = tuple(
        record_count(ref.payload_ref)
        for ref in evidence_by_kind(bundle, "pipeline_batch_manifest", target_identity=target_identity)
    )
    materialization_counts = tuple(
        materialization_count(ref.payload_ref)
        for ref in evidence_by_kind(bundle, "pipeline_materialization_refs", target_identity=target_identity)
    )
    positive_batch_or_refs = any(count > 0 for count in batch_counts + materialization_counts)
    if current_count is None:
        if positive_batch_or_refs:
            return DatabaseEmptiness.FILLED.value
        blocking.append(blocker_payload("database_emptiness_unknown", target_identity, "database content summary", "missing", ()))
        return DatabaseEmptiness.UNKNOWN.value
    if current_count == 0 and positive_batch_or_refs:
        blocking.append(blocker_payload("owner_evidence_conflict", target_identity, "empty database evidence", "batch/materialization evidence has records", ()))
        return DatabaseEmptiness.UNKNOWN.value
    if current_count > 0:
        return DatabaseEmptiness.FILLED.value
    return DatabaseEmptiness.EMPTY.value
