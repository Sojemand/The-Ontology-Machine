from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.agent_workflow_creation_runner import operation_receipt_id
from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker, RebuildWorkflowExecution
from semantic_control_kernel.workflows.rebuild.entry import database_rebuild_from_artifacts
from semantic_control_kernel.workflows.rebuild.final_notice import append_rebuild_final_notice
from semantic_control_kernel.workflows.rebuild.interaction_port import RebuildInteractionPort


def run_database_rebuild_agent_workflow(
    *,
    state_paths: StatePaths,
    rebuild_runtime,
    workflow_run_id: str | None = None,
) -> RebuildWorkflowExecution:
    runtime = rebuild_runtime(state_paths)
    resolved_workflow_run_id = workflow_run_id or generate_id("workflow_run_id")
    interaction_port = getattr(runtime, "interaction_port", None) or RebuildInteractionPort(
        state_paths,
        semantic_release_adapter=runtime.semantic_release_adapter,
    )
    collected = interaction_port.collect_rebuild_inputs(
        workflow_tool="database_rebuild_from_artifacts",
        workflow_run_id=resolved_workflow_run_id,
    )
    if collected is None:
        execution = _waiting_execution(state_paths, resolved_workflow_run_id, interaction_port)
        sync_database_rebuild_workflow_run(execution.to_dict(), state_paths=state_paths)
        return execution
    if isinstance(collected, RebuildWorkflowBlocker):
        execution = _blocked_execution(state_paths, resolved_workflow_run_id, collected)
        sync_database_rebuild_workflow_run(execution.to_dict(), state_paths=state_paths)
        return execution
    execution = database_rebuild_from_artifacts(
        runtime=runtime,
        artifact_root=collected.artifact_root,
        target_database_name=collected.target_database_name,
        overwrite_receipt=collected.overwrite_receipt,
        workflow_run_id=resolved_workflow_run_id,
        embedding_provider_configured=True,
    )
    sync_database_rebuild_workflow_run(execution.to_dict(), state_paths=state_paths)
    return execution


def sync_database_rebuild_workflow_run(execution: Mapping[str, Any], *, state_paths: StatePaths) -> None:
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
    interaction_port: RebuildInteractionPort,
) -> RebuildWorkflowExecution:
    request = interaction_port.pending_rebuild_request(workflow_run_id)
    if request is None:
        blocker = RebuildWorkflowBlocker(
            "input_missing",
            "rebuild_collect_interaction",
            "database_rebuild_from_artifacts",
            "expired_pending_interaction",
            "Rebuild target must be collected through Kernel/UI state.",
        )
        return _blocked_execution(state_paths, workflow_run_id, blocker)
    summary = str(request.payload.get("user_visible_summary") or "The Kernel is waiting for database rebuild input.")
    execution = RebuildWorkflowExecution(
        workflow_run_id=workflow_run_id,
        workflow_tool="database_rebuild_from_artifacts",
        rebuild_run_id=generate_id("rebuild_run_id"),
        state_root=state_paths.state_root,
        artifact_root="",
        target_database_path="",
    )
    execution.status = "waiting"
    execution.final_state = "awaiting_rebuild_interaction"
    execution.blocked_step_id = "rebuild_collect_interaction"
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
    blocker: RebuildWorkflowBlocker,
) -> RebuildWorkflowExecution:
    execution = RebuildWorkflowExecution(
        workflow_run_id=workflow_run_id,
        workflow_tool="database_rebuild_from_artifacts",
        rebuild_run_id=generate_id("rebuild_run_id"),
        state_root=state_paths.state_root,
        artifact_root="",
        target_database_path="",
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
    append_rebuild_final_notice(execution)
    return execution


def _pending_interaction_ref_for_workflow(state_paths: StatePaths, workflow_run_id: str) -> str | None:
    for request in InteractionRequestStore(state_paths).list_pending_interactions_for_workflow(workflow_run_id):
        interaction_request_id = str(request.payload.get("interaction_request_id") or "")
        if interaction_request_id:
            return f"pending_interactions/active/{interaction_request_id}.json"
    return None
