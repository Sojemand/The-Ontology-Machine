from __future__ import annotations

from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
)


def pending_sample_request(runtime, workflow_run_id: str):
    request_getter = getattr(runtime.interaction_port, "pending_sample_files_request", None)
    if callable(request_getter):
        return request_getter(workflow_run_id)
    return None


def wait_for_sample_files(
    runtime,
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    *,
    step_id: str,
    fallback_summary: str,
) -> None:
    pending_request = pending_sample_request(runtime, execution.workflow_run_id)
    if pending_request is None:
        return
    interaction_request_id = str(pending_request.payload["interaction_request_id"])
    summary = str(pending_request.payload.get("user_visible_summary") or fallback_summary)
    execution.status = "waiting"
    execution.blocked_step_id = step_id
    execution.artifacts["pending_interaction_request_id"] = interaction_request_id
    execution.artifacts["pending_interaction_summary"] = summary
    repository.append_progress(
        execution,
        step_id=step_id,
        status=ProgressStatus.WAITING_FOR_USER.value,
        summary=summary,
        event_type=ProgressEventType.USER_INTERACTION.value,
    )
