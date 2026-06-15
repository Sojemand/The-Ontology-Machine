from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.dialogs import RecoveryDialogService
from semantic_control_kernel.domain.recovery.partial_pipeline_run import PartialPipelineRunReconciler
from semantic_control_kernel.domain.recovery.rebind_database_artifact_tree import DatabaseArtifactRebindService
from semantic_control_kernel.domain.recovery.retry_resume import RetryResumeService
from semantic_control_kernel.domain.recovery.staged_work_archive import StagedWorkArchiveService
from semantic_control_kernel.domain.recovery.stale_lock import StaleLockRecoveryService
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.surface.recovery_tool_outputs import rejected_output
from semantic_control_kernel.surface.recovery_support_actions import (
    open_support_bundle_output,
    service_missing_recovery_output,
)


class RecoveryToolActions:
    def __init__(
        self,
        *,
        recovery_store: RecoveryEventStore,
        dialog_service: RecoveryDialogService,
        stale_lock_service: StaleLockRecoveryService | None,
        rebind_service: DatabaseArtifactRebindService,
        staged_work_service: StagedWorkArchiveService | None,
        partial_run_reconciler: PartialPipelineRunReconciler | None,
        retry_resume_service: RetryResumeService,
        support_bundle_store: SupportBundleStore,
    ) -> None:
        self.recovery_store = recovery_store
        self.dialog_service = dialog_service
        self.stale_lock_service = stale_lock_service
        self.rebind_service = rebind_service
        self.staged_work_service = staged_work_service
        self.partial_run_reconciler = partial_run_reconciler
        self.retry_resume_service = retry_resume_service
        self.support_bundle_store = support_bundle_store

    def call(
        self,
        tool_name: str,
        *,
        recovery_event: Mapping[str, Any],
        recovery_option: Mapping[str, Any],
        payload: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        if tool_name == "kernel_apply_recovery_option":
            return self.apply_option(recovery_event, recovery_option)
        if tool_name == "kernel_open_recovery_dialog":
            return self.open_dialog(recovery_event, recovery_option)
        if tool_name == "kernel_retry_recoverable_workflow":
            return self.retry(recovery_event, str(payload["recovery_id"]), evidence)
        if tool_name == "kernel_resolve_stale_lock":
            return self.resolve_lock(recovery_event, str(payload["recovery_id"]), str(payload["lock_id"]))
        if tool_name == "kernel_rebind_database_artifact_tree":
            return self.rebind(recovery_event, str(payload["recovery_id"]), str(payload["binding_recovery_id"]), evidence)
        if tool_name == "kernel_discard_or_archive_staged_work":
            return self.archive_staged_work(recovery_event, str(payload["recovery_id"]), str(payload["staged_work_ref"]), evidence)
        if tool_name == "kernel_reconcile_partial_pipeline_run":
            return self.reconcile_partial_run(recovery_event, str(payload["recovery_id"]), str(payload["partial_run_ref"]), evidence)
        if tool_name == "kernel_open_support_bundle":
            return self.open_support_bundle(recovery_event)
        return rejected_output(tool_name, None, "unknown_tool")

    def apply_option(self, recovery_event: Mapping[str, Any], recovery_option: Mapping[str, Any]) -> dict[str, Any]:
        dialog_ref = None
        next_event = {"effect": recovery_option.get("effect")}
        if recovery_option.get("kernel_dialog_action"):
            dialog = self.dialog_service.open_dialog(recovery_event, recovery_option)
            dialog_ref = dialog["dialog_request_ref"]
            next_event = None
        receipt = self._append_applied_receipt(recovery_event, recovery_option)
        return {
            "schema_version": "kernel.kernel_apply_recovery_option.output.v1",
            "result_status": "applied",
            "recovery_receipt_id": receipt.payload["recovery_receipt_id"],
            "next_kernel_event": next_event,
            "opened_dialog_ref": dialog_ref,
            "support_bundle_ref": recovery_event.get("support_bundle_ref"),
        }

    def open_dialog(self, recovery_event: Mapping[str, Any], recovery_option: Mapping[str, Any]) -> dict[str, Any]:
        dialog = self.dialog_service.open_dialog(recovery_event, recovery_option)
        receipt = self._append_applied_receipt(recovery_event, recovery_option)
        return {
            "schema_version": "kernel.kernel_open_recovery_dialog.output.v1",
            "result_status": "applied",
            "recovery_receipt_id": receipt.payload["recovery_receipt_id"],
            "dialog_request_ref": dialog["dialog_request_ref"],
            "kernel_dialog_state": dialog["kernel_dialog_state"],
        }

    def retry(self, recovery_event: Mapping[str, Any], recovery_id: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        result = self.retry_resume_service.retry(recovery_event, recovery_id, evidence)
        return {
            "schema_version": "kernel.kernel_retry_recoverable_workflow.output.v1",
            "result_status": result["result_status"],
            "new_or_resumed_workflow_run_id": result["new_or_resumed_workflow_run_id"],
            "recovery_receipt_id": result["receipt"].payload["recovery_receipt_id"],
            "progress_event_ref": result["progress_event_ref"],
            "support_bundle_ref": result["support_bundle_ref"],
        }

    def resolve_lock(self, recovery_event: Mapping[str, Any], recovery_id: str, lock_id: str) -> dict[str, Any]:
        if self.stale_lock_service is None:
            return self.service_missing("kernel_resolve_stale_lock", recovery_event, recovery_id, lock_id=lock_id)
        result = self.stale_lock_service.resolve_lock(recovery_event, recovery_id, lock_id)
        return {
            "schema_version": "kernel.kernel_resolve_stale_lock.output.v1",
            "result_status": result["result_status"],
            "lock_id": lock_id,
            "lock_status_after": result["lock_status_after"],
            "recovery_receipt_id": result["receipt"].payload["recovery_receipt_id"],
            "support_bundle_ref": result["support_bundle_ref"],
        }

    def rebind(self, recovery_event: Mapping[str, Any], recovery_id: str, binding_recovery_id: str, proof: Mapping[str, Any]) -> dict[str, Any]:
        result = self.rebind_service.rebind(recovery_event, recovery_id, binding_recovery_id, proof)
        return {
            "schema_version": "kernel.kernel_rebind_database_artifact_tree.output.v1",
            "result_status": result["result_status"],
            "binding_receipt_id": result["binding_receipt_id"],
            "recovery_receipt_id": result["receipt"].payload["recovery_receipt_id"],
            "database_artifact_binding_ref": result["database_artifact_binding_ref"],
            "support_bundle_ref": result["support_bundle_ref"],
        }

    def archive_staged_work(self, recovery_event: Mapping[str, Any], recovery_id: str, staged_work_ref: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        if self.staged_work_service is None:
            return self.service_missing("kernel_discard_or_archive_staged_work", recovery_event, recovery_id, archive_ref=None, discard_receipt_id=None)
        result = self.staged_work_service.archive_or_discard(
            recovery_event,
            recovery_id,
            staged_work_ref,
            original_refs=evidence.get("original_refs", ()),
            destructive=bool(evidence.get("destructive")),
            confirmation_ref=evidence.get("confirmation_ref"),
            scope_is_explicit=bool(evidence.get("scope_is_explicit")),
            targets_active_production=bool(evidence.get("targets_active_production")),
        )
        return {
            "schema_version": "kernel.kernel_discard_or_archive_staged_work.output.v1",
            "result_status": result["result_status"],
            "archive_ref": result["archive_ref"],
            "discard_receipt_id": result["discard_receipt_id"],
            "recovery_receipt_id": result["receipt"].payload["recovery_receipt_id"],
            "support_bundle_ref": recovery_event.get("support_bundle_ref"),
        }

    def reconcile_partial_run(self, recovery_event: Mapping[str, Any], recovery_id: str, partial_run_ref: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        if self.partial_run_reconciler is None:
            return self.service_missing("kernel_reconcile_partial_pipeline_run", recovery_event, recovery_id, finalized_manifest_ref=None, quarantine_ref=None, new_recovery_event_ref=None)
        result = self.partial_run_reconciler.reconcile(recovery_event, recovery_id, partial_run_ref, evidence)
        return {
            "schema_version": "kernel.kernel_reconcile_partial_pipeline_run.output.v1",
            "result_status": result["result_status"],
            "reconciliation_receipt_id": result["receipt"].payload["recovery_receipt_id"],
            "finalized_manifest_ref": result["finalized_manifest_ref"],
            "quarantine_ref": result["quarantine_ref"],
            "new_recovery_event_ref": result["new_recovery_event_ref"],
            "support_bundle_ref": result["support_bundle_ref"],
        }

    def open_support_bundle(self, recovery_event: Mapping[str, Any]) -> dict[str, Any]:
        return open_support_bundle_output(self.support_bundle_store, recovery_event)

    def service_missing(self, tool_name: str, recovery_event: Mapping[str, Any], recovery_id: str, **extra: Any) -> dict[str, Any]:
        return service_missing_recovery_output(self.recovery_store, tool_name, recovery_event, recovery_id, **extra)

    def _append_applied_receipt(self, recovery_event: Mapping[str, Any], recovery_option: Mapping[str, Any]):
        return self.recovery_store.append_recovery_receipt(
            recovery_event=recovery_event,
            recovery_id=recovery_option["recovery_id"],
            result_status=RecoveryResultStatus.APPLIED.value,
            selected_recovery_option=recovery_option,
        )
