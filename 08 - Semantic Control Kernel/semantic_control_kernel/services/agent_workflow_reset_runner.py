from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.agent_workflow_creation_runner import operation_receipt_id
from semantic_control_kernel.types.batches import PipelineRunBlocker, PipelineRunExecution
from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
from semantic_control_kernel.workflows.pipeline_run.reset import reset_database
from semantic_control_kernel.workflows.pipeline_run.reset_interaction_port import ResetInteractionPort


def run_database_reset_agent_workflow(
    *,
    state_paths: StatePaths,
    pipeline_runtime,
    workflow_run_id: str | None = None,
) -> PipelineRunExecution:
    runtime = pipeline_runtime(state_paths)
    resolved_workflow_run_id = workflow_run_id or generate_id("workflow_run_id")
    interaction_port = ResetInteractionPort(
        state_paths,
        corpus_adapter=runtime.corpus_adapter,
    )
    collected = interaction_port.collect_reset_inputs(
        workflow_tool="reset_database",
        workflow_run_id=resolved_workflow_run_id,
    )
    if collected is None:
        execution = _waiting_execution(state_paths, resolved_workflow_run_id, interaction_port)
        sync_database_reset_workflow_run(execution.to_dict(), state_paths=state_paths)
        return execution
    if isinstance(collected, PipelineRunBlocker):
        execution = _blocked_execution(state_paths, resolved_workflow_run_id, collected)
        sync_database_reset_workflow_run(execution.to_dict(), state_paths=state_paths)
        return execution
    execution = reset_database(
        runtime=runtime,
        target=collected.target,
        confirmation=collected.confirmation_receipt,
        workflow_run_id=resolved_workflow_run_id,
        reresolved_target_identity=collected.target.target_identity,
    )
    sync_database_reset_workflow_run(execution.to_dict(), state_paths=state_paths)
    return execution


def sync_database_reset_workflow_run(execution: Mapping[str, Any], *, state_paths: StatePaths) -> None:
    workflow_run_id = execution.get("workflow_run_id")
    if not isinstance(workflow_run_id, str) or not workflow_run_id:
        return
    run_store = WorkflowRunStore(state_paths)
    try:
        run_store.get_run(workflow_run_id)
    except ResumeStateNotFoundError:
        return
    status = str(execution.get("status") or "")
    if status == "waiting":
        pending_ref = _pending_interaction_ref_for_workflow(state_paths, workflow_run_id)
        if pending_ref:
            run_store.mark_run_waiting(workflow_run_id, pending_ref)
        return
    if status == "completed":
        run_store.mark_run_completed(workflow_run_id, operation_receipt_id(execution))
        return
    if status == "blocked":
        run_store.mark_run_failed(workflow_run_id)


def _waiting_execution(
    state_paths: StatePaths,
    workflow_run_id: str,
    interaction_port: ResetInteractionPort,
) -> PipelineRunExecution:
    request = interaction_port.pending_reset_request(workflow_run_id)
    if request is None:
        return _blocked_execution(
            state_paths,
            workflow_run_id,
            PipelineRunBlocker(
                blocker_code="input_missing",
                step_id="reset_collect_interaction",
                function_or_route="reset_database",
                recovery_state_class="expired_pending_interaction",
                user_visible_summary="Reset target must be collected through Kernel/UI state.",
            ),
        )
    summary = str(request.payload.get("user_visible_summary") or "The Kernel is waiting for database reset input.")
    execution = PipelineRunExecution(
        workflow_run_id=workflow_run_id,
        workflow_tool="reset_database",
        state_root=state_paths.state_root,
    )
    execution.status = "waiting"
    execution.final_state = "awaiting_reset_interaction"
    execution.blocked_step_id = "reset_collect_interaction"
    execution.artifacts["pending_interaction_request_id"] = str(request.payload["interaction_request_id"])
    execution.artifacts["pending_interaction_summary"] = summary
    execution.progress_events.append(
        {
            "schema_version": "kernel.progress_event.v1",
            "workflow_run_id": workflow_run_id,
            "workflow_tool": execution.workflow_tool,
            "step_id": execution.blocked_step_id,
            "step_label": execution.blocked_step_id,
            "event_type": ProgressEventType.USER_INTERACTION.value,
            "status": ProgressStatus.WAITING_FOR_USER.value,
            "sequence_index": 1,
            "user_visible_summary": summary,
            "current_state_summary": execution.final_state,
            "timestamp": utc_iso(),
        }
    )
    return execution


def _blocked_execution(
    state_paths: StatePaths,
    workflow_run_id: str,
    blocker: PipelineRunBlocker,
) -> PipelineRunExecution:
    execution = PipelineRunExecution(
        workflow_run_id=workflow_run_id,
        workflow_tool="reset_database",
        state_root=state_paths.state_root,
    )
    execution.status = "blocked"
    execution.final_state = blocker.recovery_state_class
    execution.blocked_step_id = blocker.step_id
    execution.blocker = blocker
    execution.progress_events.append(
        {
            "schema_version": "kernel.progress_event.v1",
            "workflow_run_id": workflow_run_id,
            "workflow_tool": execution.workflow_tool,
            "step_id": blocker.step_id,
            "step_label": blocker.step_id,
            "event_type": ProgressEventType.WORKFLOW_STEP.value,
            "status": ProgressStatus.BLOCKED.value,
            "sequence_index": 1,
            "user_visible_summary": blocker.user_visible_summary,
            "current_state_summary": execution.final_state,
            "timestamp": utc_iso(),
        }
    )
    return execution


def _pending_interaction_ref_for_workflow(state_paths: StatePaths, workflow_run_id: str) -> str | None:
    for request in InteractionRequestStore(state_paths).list_pending_interactions_for_workflow(workflow_run_id):
        interaction_request_id = str(request.payload.get("interaction_request_id") or "")
        if interaction_request_id:
            return f"pending_interactions/active/{interaction_request_id}.json"
    return None
