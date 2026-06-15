from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.tool_authorization import validate_recovery_option_binding
from semantic_control_kernel.policy.retry_policy import RecoveryRetryPolicy
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.types.enums import RecoveryResultStatus


class RetryResumeService:
    def __init__(self, recovery_store: RecoveryEventStore, retry_policy: RecoveryRetryPolicy | None = None) -> None:
        self.recovery_store = recovery_store
        self.retry_policy = retry_policy or RecoveryRetryPolicy()

    def retry(self, recovery_event: Mapping[str, Any], recovery_id: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        _option, binding_error = validate_recovery_option_binding(
            self.recovery_store,
            recovery_event,
            recovery_id,
            "kernel_retry_recoverable_workflow",
        )
        if binding_error is not None:
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.REJECTED.value,
                selected_recovery_option={"retry_rejection_reason": binding_error},
            )
            return {
                "new_or_resumed_workflow_run_id": None,
                "progress_event_ref": None,
                "receipt": receipt,
                "result_status": "rejected",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }
        if not self.retry_policy.can_retry_final_llm_failure(evidence):
            reason = self.retry_policy.retry_rejection_reason(evidence)
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.REJECTED.value,
                selected_recovery_option={"retry_rejection_reason": reason},
            )
            return {
                "new_or_resumed_workflow_run_id": None,
                "progress_event_ref": None,
                "receipt": receipt,
                "result_status": "rejected",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }
        resumed_id = str(evidence.get("workflow_run_id") or recovery_event["workflow_run_id"] or generate_id("workflow_run_id"))
        receipt = self.recovery_store.append_recovery_receipt(
            recovery_event=recovery_event,
            recovery_id=recovery_id,
            result_status=RecoveryResultStatus.APPLIED.value,
            selected_recovery_option={"outcome": "retry_same_workflow"},
        )
        return {
            "new_or_resumed_workflow_run_id": resumed_id,
            "progress_event_ref": {"workflow_run_id": resumed_id, "status": "retrying"},
            "receipt": receipt,
            "result_status": "applied",
            "support_bundle_ref": recovery_event.get("support_bundle_ref"),
        }
