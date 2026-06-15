from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.dialogs import RecoveryDialogService
from semantic_control_kernel.domain.recovery.partial_pipeline_run import PartialPipelineRunReconciler
from semantic_control_kernel.domain.recovery.rebind_database_artifact_tree import DatabaseArtifactRebindService
from semantic_control_kernel.domain.recovery.retry_resume import RetryResumeService
from semantic_control_kernel.domain.recovery.staged_work_archive import StagedWorkArchiveService
from semantic_control_kernel.domain.recovery.stale_lock import StaleLockRecoveryService
from semantic_control_kernel.domain.recovery.tool_authorization import RecoveryToolAuthorization
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.surface.recovery_tool_actions import RecoveryToolActions
from semantic_control_kernel.surface.recovery_tool_outputs import rejected_output
from semantic_control_kernel.validation.recovery_validation import validate_recovery_tool_input, validate_recovery_tool_output


class RecoveryToolSurface:
    def __init__(
        self,
        *,
        authorization: RecoveryToolAuthorization,
        recovery_store: RecoveryEventStore,
        dialog_service: RecoveryDialogService | None = None,
        stale_lock_service: StaleLockRecoveryService | None = None,
        rebind_service: DatabaseArtifactRebindService | None = None,
        staged_work_service: StagedWorkArchiveService | None = None,
        partial_run_reconciler: PartialPipelineRunReconciler | None = None,
        retry_resume_service: RetryResumeService | None = None,
        support_bundle_store: SupportBundleStore | None = None,
    ) -> None:
        self.authorization = authorization
        self.recovery_store = recovery_store
        self.actions = RecoveryToolActions(
            recovery_store=recovery_store,
            dialog_service=dialog_service or RecoveryDialogService(),
            stale_lock_service=stale_lock_service,
            rebind_service=rebind_service or DatabaseArtifactRebindService(recovery_store),
            staged_work_service=staged_work_service,
            partial_run_reconciler=partial_run_reconciler,
            retry_resume_service=retry_resume_service or RetryResumeService(recovery_store),
            support_bundle_store=support_bundle_store or SupportBundleStore(recovery_store.paths),
        )

    def call(self, tool_name: str, payload: Mapping[str, Any], *, service_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
        validate_recovery_tool_input(tool_name, payload)
        auth = self.authorization.authorize(
            tool_name=tool_name,
            mirror_event_id=str(payload["mirror_event_id"]),
            recovery_event_id=str(payload["recovery_event_id"]),
            recovery_id=str(payload["recovery_id"]),
        )
        if not auth.allowed:
            output = self._rejected(tool_name, payload, auth.reason)
            validate_recovery_tool_output(tool_name, output)
            return output
        output = self.actions.call(
            tool_name,
            recovery_event=dict(auth.recovery_event or {}),
            recovery_option=dict(auth.recovery_option or {}),
            payload=payload,
            evidence=dict(service_evidence or {}),
        )
        validate_recovery_tool_output(tool_name, output)
        return output

    def _rejected(self, tool_name: str, payload: Mapping[str, Any], reason: str) -> dict[str, Any]:
        recovery_receipt_id = None
        if payload.get("recovery_event_id"):
            try:
                receipt = self.recovery_store.append_rejection_receipt(
                    str(payload["recovery_event_id"]),
                    recovery_id=str(payload.get("recovery_id", "")),
                    reason=reason,
                )
                recovery_receipt_id = receipt.payload["recovery_receipt_id"]
            except Exception:
                recovery_receipt_id = None
        return rejected_output(tool_name, recovery_receipt_id, reason)
