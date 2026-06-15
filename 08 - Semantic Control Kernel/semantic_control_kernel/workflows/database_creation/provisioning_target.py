from __future__ import annotations

from typing import TYPE_CHECKING

from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
from semantic_control_kernel.workflows.database_creation.provisioning_runner import run_or_block
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    complete_step,
    create_blocker,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.routes import DatabaseCreationRuntime


def collect_creation_target_or_wait(
    runtime: "DatabaseCreationRuntime",
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
) -> DatabaseCreationBlocker | None:
    if execution.target is None:
        execution.target = runtime.interaction_port.collect_creation_target(
            workflow_tool=execution.workflow_tool,
            workflow_run_id=execution.workflow_run_id,
        )
    if execution.target is None:
        return _wait_for_pending_target_request(runtime, repository, execution)
    execution.artifacts["target"] = execution.target.to_dict()
    complete_step(
        repository,
        execution,
        step_id="dc_collect_target",
        function_name="collect_database_creation_target",
        output_refs=[execution.target.to_dict()],
    )
    return None


def _wait_for_pending_target_request(
    runtime: "DatabaseCreationRuntime",
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
) -> DatabaseCreationBlocker | None:
    pending_request = _pending_creation_target_request(runtime, execution.workflow_run_id)
    if pending_request is None:
        return create_blocker(
            step_id="dc_collect_target",
            function_or_route="create_standard_artifact_folder_tree",
            blocker_code="input_missing",
            recovery_state_class="expired_pending_interaction",
            summary="Database creation target must be collected through Kernel/UI state.",
        )
    execution.status = "waiting"
    execution.blocked_step_id = "dc_collect_target"
    execution.artifacts["pending_interaction_request_id"] = str(pending_request.payload["interaction_request_id"])
    execution.artifacts["pending_interaction_summary"] = str(
        pending_request.payload.get("user_visible_summary")
        or "The Kernel is waiting for database creation input."
    )
    repository.append_progress(
        execution,
        step_id="dc_collect_target",
        status=ProgressStatus.WAITING_FOR_USER.value,
        summary=str(execution.artifacts["pending_interaction_summary"]),
        event_type=ProgressEventType.USER_INTERACTION.value,
    )
    return None


def _pending_creation_target_request(runtime: "DatabaseCreationRuntime", workflow_run_id: str):
    request_getter = getattr(runtime.interaction_port, "pending_creation_target_request", None)
    if callable(request_getter):
        return request_getter(workflow_run_id)
    return None


def step_collect_target(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    run_or_block(runtime, repository, execution, collect_creation_target_or_wait)
