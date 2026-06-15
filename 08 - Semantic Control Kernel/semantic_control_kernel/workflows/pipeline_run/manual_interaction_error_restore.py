from __future__ import annotations

from typing import Mapping

from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.types.batches import PipelineRunBlocker, PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.input_inventory import count_error_case_sources
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_helpers import (
    input_blocker,
    orchestrator_ui_state,
    restore_confirmation_identity,
)
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_progress import ManualPipelineInteractionProgress
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_requests import open_error_case_restore_confirmation
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime, adapter_failure_summary


def recover_empty_input_if_possible() -> bool | PipelineRunBlocker | None:
    return input_blocker("Manual pipeline run requires files in the selected Artifact Tree Input folder.")


def restore_error_cases_if_requested(
    *,
    runtime: PipelineRunRuntime,
    workflow_run_store: WorkflowRunStore,
    user_interaction_service: KernelUserInteractionService,
    workflow_tool: str,
    workflow_run_id: str,
    progress: ManualPipelineInteractionProgress,
    target: PipelineRunTarget,
    input_files_present: bool,
) -> bool | PipelineRunBlocker | None:
    error_case_count = count_error_case_sources(target.artifact_root_path)
    if not error_case_count:
        return False
    if progress.latest_error_restore_decision == "confirmed":
        return restore_error_cases(runtime, workflow_tool=workflow_tool, workflow_run_id=workflow_run_id, target=target)
    if progress.latest_error_restore_decision:
        if input_files_present:
            return False
        return input_blocker("Error Case restore was not confirmed, so ingestion was not started.")
    workflow_run_store.mark_run_running(
        workflow_run_id,
        target_identity=restore_confirmation_identity(target, "error_cases"),
        resume_state_ref="",
    )
    open_error_case_restore_confirmation(
        user_interaction_service,
        workflow_tool=workflow_tool,
        workflow_run_id=workflow_run_id,
        target=target,
        error_case_count=error_case_count,
        input_files_present=input_files_present,
    )
    return None


def restore_error_cases(
    runtime: PipelineRunRuntime,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    target: PipelineRunTarget,
) -> bool | PipelineRunBlocker:
    result = runtime.orchestrator_adapter.reset_error_cases(
        {
            "workflow_run_id": workflow_run_id,
            "target_identity": target.target_identity,
            "ui_state": orchestrator_ui_state(target),
        }
    )
    if isinstance(result, MissingCapabilityBlocker):
        payload = result.to_dict()
        return PipelineRunBlocker(
            blocker_code="pipeline_capability_missing",
            step_id="restoring_error_cases",
            function_or_route=str(payload.get("kernel_function", workflow_tool)),
            recovery_state_class=str(payload.get("recovery_state_class", "support_only_unrecoverable")),
            user_visible_summary=str(payload.get("blocking_reason", "Required Pipeline capability is missing.")),
            diagnostics=tuple(dict(item) for item in payload.get("diagnostics", []) if isinstance(item, Mapping)),
        )
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return PipelineRunBlocker(
            blocker_code=result.status,
            step_id="restoring_error_cases",
            function_or_route=workflow_tool,
            recovery_state_class="missing_manifest_or_originals",
            user_visible_summary=f"{adapter_failure_summary(result).rstrip('.')} while restoring Error Cases.",
            diagnostics=tuple(dict(item) for item in result.to_dict().get("diagnostics", []) if isinstance(item, Mapping)),
        )
    return True


__all__ = [
    "recover_empty_input_if_possible",
    "restore_error_cases",
    "restore_error_cases_if_requested",
]
