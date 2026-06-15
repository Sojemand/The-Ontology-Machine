from __future__ import annotations

from dataclasses import dataclass

from semantic_control_kernel.types.enums import RecoveryStateClass


@dataclass(frozen=True)
class RecoveryMatrixEntry:
    recovery_state: str
    detectors: tuple[str, ...]
    blocked_functions: tuple[str, ...]
    recovery_options: tuple[str, ...]
    direct_kernel_dialog: str | None
    event_scoped_agent_tools: tuple[str, ...]
    required_receipt: str
    post_state: str
    must_not: str


class RecoveryMatrix:
    def __init__(self, entries: dict[str, RecoveryMatrixEntry] | None = None) -> None:
        self.entries = entries or RECOVERY_MATRIX

    def get(self, recovery_state: str) -> RecoveryMatrixEntry:
        return self.entries[recovery_state]

    def assert_complete(self) -> None:
        missing = set(RecoveryStateClass.values()) - set(self.entries)
        if missing:
            raise ValueError(f"Recovery matrix missing state(s): {', '.join(sorted(missing))}")

    def allowed_tools_for_state(self, recovery_state: str) -> tuple[str, ...]:
        return self.get(recovery_state).event_scoped_agent_tools


RECOVERY_MATRIX: dict[str, RecoveryMatrixEntry] = {
    RecoveryStateClass.STALE_LOCK.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.STALE_LOCK.value,
        detectors=("KernelStateResolver", "LockStore", "active owner heartbeat timeout"),
        blocked_functions=("workflows targeting locked resource",),
        recovery_options=("inspect_status", "keep_waiting", "resolve_stale_lock", "open_support_bundle"),
        direct_kernel_dialog="stale_lock_dialog",
        event_scoped_agent_tools=(
            "kernel_status",
            "kernel_resolve_stale_lock",
            "kernel_open_recovery_dialog",
            "kernel_open_support_bundle",
        ),
        required_receipt="kernel.recovery_receipt.v1 for every lock status change or rejected unlock",
        post_state="lock active, released, failed or pending_resume",
        must_not="force-unlock live owner or skip owner liveness proof",
    ),
    RecoveryStateClass.TARGET_IDENTITY_CHANGED.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        detectors=("KernelStateResolver", "ConfirmationService", "WorkflowResumeStore"),
        blocked_functions=("pending confirmation", "resume", "destructive operation", "activation", "merge"),
        recovery_options=("reopen_target_dialog", "inspect_resume_state", "cancel_workflow", "discard_or_archive_staged_work"),
        direct_kernel_dialog="path_reselection_dialog or discard_or_archive_staged_work_dialog",
        event_scoped_agent_tools=(
            "kernel_open_recovery_dialog",
            "kernel_resume_state",
            "kernel_cancel_active_run",
            "kernel_discard_or_archive_staged_work",
        ),
        required_receipt="recovery receipt for rejected stale input, cancellation or archive/discard",
        post_state="target reselected, workflow cancelled, stale state archived or workflow remains blocked",
        must_not="accept stale path, stale confirmation or stale target hash",
    ),
    RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value,
        detectors=("DatabaseArtifactBindingRegistry", "KernelStateResolver"),
        blocked_functions=("custom DB selection", "pipeline_run", "merge", "rebuild"),
        recovery_options=("rebind_db_artifact_tree", "open_selection_dialog", "support_only"),
        direct_kernel_dialog="rebind_database_artifact_tree_dialog",
        event_scoped_agent_tools=(
            "kernel_rebind_database_artifact_tree",
            "kernel_open_recovery_dialog",
            "kernel_open_support_bundle",
        ),
        required_receipt="rebind receipt or support-only recovery receipt",
        post_state="binding valid or operation remains blocked",
        must_not="guess binding from similar folder names",
    ),
    RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value,
        detectors=("KernelStateResolver", "activation step", "release validation"),
        blocked_functions=("pipeline_run", "activation", "release-dependent workflows"),
        recovery_options=("continue_missing_release_workflow", "reopen_dialog", "inspect_resume", "archive_or_discard", "support_bundle"),
        direct_kernel_dialog="discard_or_archive_staged_work_dialog or continuation dialog",
        event_scoped_agent_tools=(
            "create_custom_taxonomy_path",
            "create_custom_projection_path",
            "kernel_resume_state",
            "kernel_open_recovery_dialog",
            "kernel_discard_or_archive_staged_work",
            "kernel_open_support_bundle",
        ),
        required_receipt="operation receipt for continuation; recovery receipt for archive/discard/rejection",
        post_state="release active, incomplete staged state preserved or staged state archived",
        must_not="silently activate incomplete release or let Agent fabricate missing schema",
    ),
    RecoveryStateClass.PARTIAL_PIPELINE_RUN.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.PARTIAL_PIPELINE_RUN.value,
        detectors=("PartialPipelineRunReconciler", "ReceiptStore", "Phase 11 batch manifest audit"),
        blocked_functions=("subsequent pipeline_run",),
        recovery_options=("finalize_manifest", "quarantine_partial_output", "support_bundle"),
        direct_kernel_dialog="partial_pipeline_run_recovery_dialog",
        event_scoped_agent_tools=(
            "kernel_reconcile_partial_pipeline_run",
            "kernel_open_recovery_dialog",
            "kernel_open_support_bundle",
        ),
        required_receipt="recovery receipt and operation receipt for finalize or quarantine",
        post_state="proven complete, quarantined or support-only blocked",
        must_not="treat partial data as complete without proof",
    ),
    RecoveryStateClass.UNRESOLVED_MERGE_COLLISION.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.UNRESOLVED_MERGE_COLLISION.value,
        detectors=("Phase 12 collision manifest", "reconciliation validators"),
        blocked_functions=("merge finalization", "activation"),
        recovery_options=("reopen_merge_reconciliation", "cancel_merge", "archive_or_discard_merge_target", "support_bundle"),
        direct_kernel_dialog="merge_reconciliation_dialog",
        event_scoped_agent_tools=(
            "kernel_open_recovery_dialog",
            "kernel_cancel_active_run",
            "kernel_discard_or_archive_staged_work",
            "kernel_open_support_bundle",
        ),
        required_receipt="reconciliation receipt, cancellation receipt or archive/discard receipt",
        post_state="merge continues with resolved manifest or target safely abandoned",
        must_not="silently choose semantic/duplicate policy",
    ),
    RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value,
        detectors=("Batch manifest reader", "Artifact Tree audit", "manual pipeline manifest audit"),
        blocked_functions=("pipeline_run", "rebuild audit"),
        recovery_options=("reopen_missing_input_dialog", "support_bundle", "manual_filesystem_action_via_dialog"),
        direct_kernel_dialog="missing_input_dialog or support dialog",
        event_scoped_agent_tools=("kernel_open_recovery_dialog", "kernel_open_support_bundle", "kernel_cancel_active_run"),
        required_receipt="recovery receipt for dialog resolution, cancellation or support-only",
        post_state="manual pipeline path continues or remains blocked",
        must_not="delete records when affected set cannot be isolated",
    ),
    RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value,
        detectors=("LLMFunctionAdapter after Phase 8 retry exhaustion",),
        blocked_functions=("current LLM-supplemented workflow step",),
        recovery_options=("retry_same_workflow", "cancel", "inspect_resume", "support_bundle", "apply_bound_option"),
        direct_kernel_dialog=None,
        event_scoped_agent_tools=(
            "kernel_retry_recoverable_workflow",
            "kernel_cancel_active_run",
            "kernel_resume_state",
            "kernel_open_support_bundle",
            "kernel_apply_recovery_option",
        ),
        required_receipt="recovery receipt for retry/cancel/support; failed attempt refs persisted by Phase 8",
        post_state="workflow retried, cancelled, resumable or support-only final error",
        must_not="consume invalid JSON or ask Agent/user to repair JSON",
    ),
    RecoveryStateClass.EXPIRED_PENDING_INTERACTION.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.EXPIRED_PENDING_INTERACTION.value,
        detectors=("UserInteractionAdapter", "WorkflowResumeStore"),
        blocked_functions=("pending input", "selection", "confirmation"),
        recovery_options=("reopen_dialog_if_identity_matches", "inspect_resume", "cancel_workflow"),
        direct_kernel_dialog="original dialog reopened as recovery dialog",
        event_scoped_agent_tools=("kernel_open_recovery_dialog", "kernel_resume_state", "kernel_cancel_active_run"),
        required_receipt="recovery receipt for reopened, rejected stale or cancelled interaction",
        post_state="pending interaction active again or workflow blocked/cancelled",
        must_not="accept expired dialog response",
    ),
    RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value: RecoveryMatrixEntry(
        recovery_state=RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value,
        detectors=("any recovery service", "unknown exception", "missing capability with no safe recovery"),
        blocked_functions=("current workflow continuation",),
        recovery_options=("open_support_bundle", "cancel_when_valid", "archive_or_discard_when_safe"),
        direct_kernel_dialog="support_bundle_dialog",
        event_scoped_agent_tools=(
            "kernel_open_support_bundle",
            "kernel_cancel_active_run",
            "kernel_discard_or_archive_staged_work",
        ),
        required_receipt="support-only receipt plus cancellation/archive receipt if applied",
        post_state="terminal support-visible state or safe abandonment",
        must_not="invent recovery options",
    ),
}
