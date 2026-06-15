from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.database_creation_interaction_resume import (
    database_creation_interaction_resume_inputs,
)
from semantic_control_kernel.workflows.database_creation import run_database_creation_workflow


def run_database_creation_agent_workflow(
    tool_name: str,
    *,
    state_paths: StatePaths,
    database_creation_runtime,
    workflow_run_id: str | None = None,
    resume_from_progress: bool = False,
):
    runtime = database_creation_runtime(state_paths)
    resume_inputs = (
        database_creation_interaction_resume_inputs(
            workflow_run_id=workflow_run_id,
            state_paths=state_paths,
        )
        if resume_from_progress and workflow_run_id
        else None
    )
    execution = run_database_creation_workflow(
        tool_name,
        runtime=runtime,
        workflow_run_id=workflow_run_id,
        target=resume_inputs.target if resume_inputs is not None else None,
        initial_artifacts=resume_inputs.artifacts if resume_inputs is not None else None,
        initial_final_state=resume_inputs.final_state if resume_inputs is not None else "unknown",
        initial_completed_step_ids=resume_inputs.completed_step_ids if resume_inputs is not None else (),
    )
    sync_database_creation_workflow_run(execution.to_dict(), state_paths=state_paths)
    return execution


def sync_database_creation_workflow_run(execution: Mapping[str, Any], *, state_paths: StatePaths) -> None:
    workflow_run_id = string_or_none(execution.get("workflow_run_id"))
    if not workflow_run_id:
        return
    run_store = WorkflowRunStore(state_paths)
    try:
        run_store.get_run(workflow_run_id)
    except ResumeStateNotFoundError:
        return
    status = str(execution.get("status") or "")
    if status == "waiting":
        pending_ref = pending_interaction_ref_for_workflow(state_paths, workflow_run_id)
        if pending_ref:
            run_store.mark_run_waiting(workflow_run_id, pending_ref)
        return
    if status == "completed":
        run_store.mark_run_completed(workflow_run_id, operation_receipt_id(execution))
        return
    if status == "blocked":
        run_store.mark_run_failed(workflow_run_id)


def include_optional_database_creation_resume(workflow_tool: str, initial_final_state: str) -> bool:
    return (
        workflow_tool == "create_custom_projection_path"
        and initial_final_state == "semantic_release_incomplete"
    ) or (
        workflow_tool == "create_custom_taxonomy_path"
        and initial_final_state == "no_semantic_release"
    )


def pending_interaction_ref_for_workflow(state_paths: StatePaths, workflow_run_id: str) -> str | None:
    for request in InteractionRequestStore(state_paths).list_pending_interactions_for_workflow(workflow_run_id):
        interaction_request_id = str(request.payload.get("interaction_request_id") or "")
        if interaction_request_id:
            return f"pending_interactions/active/{interaction_request_id}.json"
    return None


def operation_receipt_id(execution: Mapping[str, Any]) -> str:
    receipts = execution.get("operation_receipts")
    if isinstance(receipts, list) and receipts:
        latest = receipts[-1]
        if isinstance(latest, Mapping):
            return str(latest.get("operation_receipt_id") or "")
    return str(execution.get("workflow_run_id") or "")


def string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None
