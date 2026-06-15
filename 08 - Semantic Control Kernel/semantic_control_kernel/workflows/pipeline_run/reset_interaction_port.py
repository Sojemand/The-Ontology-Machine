from __future__ import annotations

from typing import Any

from semantic_control_kernel.policy.cleanup_policy import destructive_confirmation_matches
from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.batches import PipelineRunBlocker
from semantic_control_kernel.types.events import UserInteractionRequest
from semantic_control_kernel.workflows.pipeline_run.reset_interaction_helpers import (
    _clean_path,
    _clean_text,
    _input_blocker,
    _interaction_target_identity,
    _reset_placeholder_identity,
)
from semantic_control_kernel.workflows.pipeline_run.reset_interaction_release import read_active_release
from semantic_control_kernel.workflows.pipeline_run.reset_interaction_requests import (
    open_next_interaction,
    open_reset_confirmation,
    progress_from_recorded_responses,
)
from semantic_control_kernel.workflows.pipeline_run.reset_interaction_types import (
    RESET_INTERACTION_FUNCTIONS,
    ResetInteractionInputs,
    _InlineClientFrontendEventSink,
)
from semantic_control_kernel.workflows.pipeline_run.target_resolution import target_from_active_release
from semantic_control_kernel.workflows.rebuild.target_path import resolve_target_database


class ResetInteractionPort:
    def __init__(
        self,
        state_paths: StatePaths,
        *,
        corpus_adapter: Any,
        interaction_store: InteractionRequestStore | None = None,
        workflow_run_store: WorkflowRunStore | None = None,
        receipt_store: ReceiptStore | None = None,
        user_interaction_service: KernelUserInteractionService | None = None,
    ) -> None:
        self.state_paths = state_paths
        self.corpus_adapter = corpus_adapter
        self.interaction_store = interaction_store or InteractionRequestStore(state_paths)
        self.workflow_run_store = workflow_run_store or WorkflowRunStore(state_paths)
        self.receipt_store = receipt_store or ReceiptStore(state_paths)
        self.user_interaction_service = user_interaction_service or KernelUserInteractionService(
            interaction_store=self.interaction_store,
            mirror_event_service=KernelMirrorEventService(MirrorEventStore(state_paths)),
            event_sink=_InlineClientFrontendEventSink(),
            workflow_run_store=self.workflow_run_store,
            receipt_store=self.receipt_store,
        )

    def collect_reset_inputs(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
    ) -> ResetInteractionInputs | PipelineRunBlocker | None:
        self._ensure_workflow_run(workflow_tool, workflow_run_id)
        progress = progress_from_recorded_responses(self.interaction_store, workflow_run_id)
        if progress.next_interaction_function is not None:
            if self.pending_reset_request(workflow_run_id) is None:
                open_next_interaction(
                    self.user_interaction_service,
                    workflow_tool=workflow_tool,
                    workflow_run_id=workflow_run_id,
                    progress=progress,
                )
            return None
        artifact_root = _clean_path(progress.artifact_root)
        target_database_name = _clean_text(progress.target_database_name)
        if artifact_root is None or target_database_name is None:
            return _input_blocker("Reset Artifact Tree and database name must be collected through Kernel/UI state.")
        try:
            target_path, _target_identity = resolve_target_database(
                artifact_root=artifact_root,
                target_database_name=target_database_name,
            )
        except ValueError as exc:
            return PipelineRunBlocker(
                blocker_code="invalid_target_path",
                step_id="reset_collect_interaction",
                function_or_route=workflow_tool,
                recovery_state_class="target_identity_changed",
                user_visible_summary=str(exc),
            )
        if not target_path.exists():
            return PipelineRunBlocker(
                blocker_code="database_missing",
                step_id="reset_resolve_database",
                function_or_route=workflow_tool,
                recovery_state_class="target_identity_changed",
                user_visible_summary="The selected reset target database does not exist.",
                diagnostics=({"target_database_path": str(target_path)},),
            )
        loaded, blocker = read_active_release(
            self.corpus_adapter,
            workflow_tool=workflow_tool,
            target_database_path=target_path,
        )
        if blocker is not None:
            return blocker
        target = target_from_active_release(
            workflow_run_id=workflow_run_id,
            artifact_root=artifact_root,
            target_database_path=target_path,
            loaded_release=loaded,
        )
        receipt = self._matching_reset_receipt(target)
        if receipt is not None:
            self.workflow_run_store.mark_run_running(
                workflow_run_id,
                target_identity=_interaction_target_identity(target),
                resume_state_ref="",
            )
            return ResetInteractionInputs(target=target, confirmation_receipt=receipt)
        if progress.latest_confirmation_decision and progress.latest_confirmation_decision != "confirmed":
            return PipelineRunBlocker(
                blocker_code="confirmation_missing",
                step_id="confirming_reset",
                function_or_route=workflow_tool,
                recovery_state_class="expired_pending_interaction",
                user_visible_summary="Database reset was not confirmed, so the target database was left unchanged.",
            )
        self.workflow_run_store.mark_run_running(
            workflow_run_id,
            target_identity=_interaction_target_identity(target),
            resume_state_ref="",
        )
        if self.pending_reset_request(workflow_run_id) is None:
            open_reset_confirmation(
                self.user_interaction_service,
                workflow_tool=workflow_tool,
                workflow_run_id=workflow_run_id,
                target=target,
            )
        return None

    def pending_reset_request(self, workflow_run_id: str) -> UserInteractionRequest | None:
        for request in self.interaction_store.list_pending_interactions_for_workflow(workflow_run_id):
            if request.payload.get("function_or_route") != "reset_database":
                continue
            if request.payload.get("interaction_function") in RESET_INTERACTION_FUNCTIONS:
                return request
        return None

    def _ensure_workflow_run(self, workflow_tool: str, workflow_run_id: str) -> None:
        try:
            self.workflow_run_store.get_run(workflow_run_id)
        except ResumeStateNotFoundError:
            self.workflow_run_store.create_run(
                workflow_tool,
                _reset_placeholder_identity(workflow_run_id),
                "kernel_database_reset_target_collection",
                workflow_run_id=workflow_run_id,
            )

    def _matching_reset_receipt(self, target) -> dict[str, Any] | None:
        for receipt in reversed(self.receipt_store.list_by_target(_interaction_target_identity(target))):
            payload = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
            ok, _reason = destructive_confirmation_matches(
                payload,
                target_identity=target.target_identity,
                state_snapshot_id=target.state_snapshot_id,
                confirmation_scope="reset_database",
            )
            if ok:
                return dict(payload)
        return None
