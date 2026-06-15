from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.tool_authorization import validate_recovery_option_binding
from semantic_control_kernel.repository._helpers import require_same_identity
from semantic_control_kernel.repository.errors import TargetIdentityMismatchError
from semantic_control_kernel.repository.lock_store import LockStore
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.types.enums import LockStatus, RecoveryResultStatus


class StaleLockRecoveryService:
    def __init__(self, lock_store: LockStore, recovery_store: RecoveryEventStore) -> None:
        self.lock_store = lock_store
        self.recovery_store = recovery_store

    def resolve_lock(self, recovery_event: Mapping[str, Any], recovery_id: str, lock_id: str) -> dict[str, Any]:
        lock = self.lock_store.get_lock(lock_id)
        _option, binding_error = validate_recovery_option_binding(
            self.recovery_store,
            recovery_event,
            recovery_id,
            "kernel_resolve_stale_lock",
        )
        if binding_error is not None:
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.REJECTED.value,
                selected_recovery_option={"lock_id": lock_id, "rejection_reason": binding_error},
            )
            return {
                "lock_id": lock_id,
                "lock_status_after": lock.payload["status"],
                "receipt": receipt,
                "result_status": "rejected",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }
        evidence = dict(lock.payload.get("liveness_evidence", {}))
        target_mismatch = _target_identity_mismatch(lock.payload, recovery_event)
        if target_mismatch is not None:
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.REJECTED.value,
                selected_recovery_option={"lock_id": lock_id, "rejection_reason": target_mismatch},
            )
            return {
                "lock_id": lock_id,
                "lock_status_after": lock.payload["status"],
                "receipt": receipt,
                "result_status": "rejected",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }
        outcome = _classify_liveness(evidence)

        if outcome == "owner_live_or_uncertain":
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.REJECTED.value,
                selected_recovery_option={"outcome": outcome, "lock_id": lock_id},
            )
            return {
                "lock_id": lock_id,
                "lock_status_after": lock.payload["status"],
                "receipt": receipt,
                "result_status": "rejected",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }

        if outcome == "pending_resume":
            updated = self.lock_store.mark_pending_resume(lock_id, {"workflow_run_id": lock.payload["owner_workflow_run_id"]})
            result_status = RecoveryResultStatus.APPLIED.value
        elif outcome == "failed":
            updated = self.lock_store.mark_failed(lock_id, "partial_mutation_risk", {"recovery_event_id": recovery_event["recovery_event_id"]})
            result_status = RecoveryResultStatus.APPLIED.value
        else:
            updated = self.lock_store.release(lock_id, "owner_dead_no_partial_mutation", {"recovery_event_id": recovery_event["recovery_event_id"]})
            result_status = RecoveryResultStatus.APPLIED.value

        receipt = self.recovery_store.append_recovery_receipt(
            recovery_event=recovery_event,
            recovery_id=recovery_id,
            result_status=result_status,
            selected_recovery_option={"outcome": outcome, "lock_id": lock_id},
            mutated_refs=[{"lock_id": lock_id, "status": updated.payload["status"]}],
        )
        return {
            "lock_id": lock_id,
            "lock_status_after": updated.payload["status"],
            "receipt": receipt,
            "result_status": "applied",
            "support_bundle_ref": recovery_event.get("support_bundle_ref"),
        }


def _target_identity_mismatch(lock_payload: Mapping[str, Any], recovery_event: Mapping[str, Any]) -> str | None:
    try:
        require_same_identity(
            recovery_event.get("target_identity") if isinstance(recovery_event.get("target_identity"), Mapping) else {},
            lock_payload.get("target_identity") if isinstance(lock_payload.get("target_identity"), Mapping) else {},
            "stale lock recovery target",
        )
    except TargetIdentityMismatchError:
        return "target_identity_changed"
    return None


def _classify_liveness(evidence: Mapping[str, Any]) -> str:
    if evidence.get("owner_live") is True or evidence.get("pipeline_run_status") == "running":
        return "owner_live_or_uncertain"
    if evidence.get("owner_live") is None and evidence.get("owner_dead") is not True:
        return "owner_live_or_uncertain"
    if evidence.get("partial_mutation_risk") is True:
        return "failed"
    if evidence.get("safe_resume_point") is True:
        return "pending_resume"
    return LockStatus.RELEASED.value
