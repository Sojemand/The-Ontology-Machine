from __future__ import annotations

from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.batches import PipelineRunBlocker
from semantic_control_kernel.types.events import UserInteractionRequest
from semantic_control_kernel.workflows.pipeline_run.input_inventory import scan_input_files
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_error_restore import (
    recover_empty_input_if_possible,
    restore_error_cases_if_requested,
)
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_helpers import (
    clean_path,
    input_blocker,
    input_confirmation_identity,
    pipeline_confirmation,
)
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_port_state import (
    ManualPipelineInteractionInputs,
    build_user_interaction_service,
    ensure_workflow_run,
    pending_pipeline_request as _pending_pipeline_request,
    pending_pipeline_request_ref as _pending_pipeline_request_ref,
    pending_pipeline_summary as _pending_pipeline_summary,
)
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_progress import progress_from_recorded_responses
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_requests import (
    open_choose_artifact_root,
    open_input_confirmation,
    open_name_database,
)
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_target import (
    matching_input_confirmation_receipt,
    read_active_release,
    resolve_database_path,
)
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime
from semantic_control_kernel.workflows.pipeline_run.target_resolution import target_from_active_release


class ManualPipelineInteractionPort:
    def __init__(
        self,
        state_paths: StatePaths,
        *,
        runtime: PipelineRunRuntime,
        interaction_store: InteractionRequestStore | None = None,
        workflow_run_store: WorkflowRunStore | None = None,
        receipt_store: ReceiptStore | None = None,
        user_interaction_service: KernelUserInteractionService | None = None,
    ) -> None:
        self.state_paths = state_paths
        self.runtime = runtime
        self.interaction_store = interaction_store or InteractionRequestStore(state_paths)
        self.workflow_run_store = workflow_run_store or WorkflowRunStore(state_paths)
        self.receipt_store = receipt_store or ReceiptStore(state_paths)
        self.user_interaction_service = user_interaction_service or build_user_interaction_service(
            state_paths,
            interaction_store=self.interaction_store,
            workflow_run_store=self.workflow_run_store,
            receipt_store=self.receipt_store,
        )

    def collect_pipeline_inputs(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
    ) -> ManualPipelineInteractionInputs | PipelineRunBlocker | None:
        ensure_workflow_run(self.workflow_run_store, workflow_tool, workflow_run_id)
        progress = progress_from_recorded_responses(self.interaction_store, workflow_run_id)
        if progress.next_interaction_function is not None:
            if self.pending_pipeline_request(workflow_run_id) is None:
                open_choose_artifact_root(
                    self.user_interaction_service,
                    workflow_tool=workflow_tool,
                    workflow_run_id=workflow_run_id,
                    progress=progress,
                )
            return None
        artifact_root = clean_path(progress.artifact_root)
        if artifact_root is None:
            return input_blocker("Manual pipeline run Artifact Tree must be collected through Kernel/UI state.")
        target_path, name_needed, blocker = resolve_database_path(
            workflow_tool=workflow_tool,
            workflow_run_id=workflow_run_id,
            artifact_root=artifact_root,
            target_database_name=progress.target_database_name,
        )
        if blocker is not None:
            return blocker
        if name_needed:
            if self.pending_pipeline_request(workflow_run_id) is None:
                open_name_database(
                    self.user_interaction_service,
                    workflow_tool=workflow_tool,
                    workflow_run_id=workflow_run_id,
                    artifact_root=artifact_root,
                )
            return None
        if target_path is None:
            return input_blocker("Manual pipeline run target database could not be resolved.")
        loaded, blocker = read_active_release(
            self.runtime,
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
        input_files = scan_input_files(target)
        restored_error_cases = restore_error_cases_if_requested(
            runtime=self.runtime,
            workflow_run_store=self.workflow_run_store,
            user_interaction_service=self.user_interaction_service,
            workflow_tool=workflow_tool,
            workflow_run_id=workflow_run_id,
            progress=progress,
            target=target,
            input_files_present=bool(input_files),
        )
        if restored_error_cases is None:
            return None
        if isinstance(restored_error_cases, PipelineRunBlocker):
            return restored_error_cases
        if restored_error_cases:
            input_files = scan_input_files(target)
        if not input_files:
            recovered = recover_empty_input_if_possible()
            if recovered is None:
                return None
            if isinstance(recovered, PipelineRunBlocker):
                return recovered
            input_files = scan_input_files(target)
            if not input_files:
                return input_blocker("No Input files were available after the selected recovery step.")
        receipt = matching_input_confirmation_receipt(self.receipt_store, target, input_files)
        if receipt is not None:
            self.workflow_run_store.mark_run_running(
                workflow_run_id,
                target_identity=target.target_identity,
                resume_state_ref="",
            )
            return ManualPipelineInteractionInputs(
                target=target,
                input_files=tuple(input_files),
                confirmation_receipt=pipeline_confirmation(target, input_files, receipt),
            )
        if progress.latest_input_decision and progress.latest_input_decision != "confirmed":
            return PipelineRunBlocker(
                blocker_code="confirmation_missing",
                step_id="confirming_input_presence",
                function_or_route=workflow_tool,
                recovery_state_class="expired_pending_interaction",
                user_visible_summary="Manual pipeline run was not confirmed, so no ingestion was started.",
            )
        self.workflow_run_store.mark_run_running(
            workflow_run_id,
            target_identity=input_confirmation_identity(target, input_files),
            resume_state_ref="",
        )
        if self.pending_pipeline_request(workflow_run_id) is None:
            open_input_confirmation(
                self.user_interaction_service,
                workflow_tool=workflow_tool,
                workflow_run_id=workflow_run_id,
                target=target,
                input_files=input_files,
            )
        return None

    def pending_pipeline_request(self, workflow_run_id: str) -> UserInteractionRequest | None:
        return _pending_pipeline_request(self.interaction_store, workflow_run_id)

    def pending_pipeline_request_ref(self, workflow_run_id: str) -> str | None:
        return _pending_pipeline_request_ref(self.interaction_store, workflow_run_id)

    def pending_pipeline_summary(self, workflow_run_id: str) -> str:
        return _pending_pipeline_summary(self.interaction_store, workflow_run_id)
