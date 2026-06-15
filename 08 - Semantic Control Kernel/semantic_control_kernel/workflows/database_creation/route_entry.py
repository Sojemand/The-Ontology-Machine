from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.types.database_creation import DatabaseCreationTarget
from semantic_control_kernel.workflows.database_creation.route_dispatch import run_database_creation_step
from semantic_control_kernel.workflows.database_creation.route_resume import build_and_store_resume
from semantic_control_kernel.workflows.database_creation.route_runtime import DatabaseCreationRuntime
from semantic_control_kernel.workflows.database_creation.route_sequences import route_sequence
from semantic_control_kernel.workflows.database_creation.route_state import (
    final_state_for_completed_route,
    target_from_runtime,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    DatabaseCreationExecution,
    final_notice,
    progress_started,
)


def run_database_creation_workflow(
    workflow_tool: str,
    *,
    runtime: DatabaseCreationRuntime,
    workflow_run_id: str | None = None,
    target: DatabaseCreationTarget | None = None,
    initial_artifacts: Mapping[str, object] | None = None,
    initial_final_state: str = "unknown",
    initial_completed_step_ids: Sequence[str] = (),
    include_optional_steps: bool = False,
) -> DatabaseCreationExecution:
    repository = runtime.state_repository()
    resolved_target = target or target_from_runtime(runtime)
    execution = DatabaseCreationExecution(
        workflow_run_id=workflow_run_id or generate_id("workflow_run_id"),
        workflow_tool=workflow_tool,
        state_root=Path(runtime.state_root),
        target=resolved_target,
        final_state=initial_final_state,
        completed_step_ids=list(initial_completed_step_ids),
        completed_step_ids_at_run_start=list(initial_completed_step_ids),
        satisfied_precondition_step_ids=list(initial_completed_step_ids),
        artifacts=dict(initial_artifacts or {}),
    )
    execution._sequence_index = len(repository.progress.list_progress_events(execution.workflow_run_id))
    sequence = route_sequence(workflow_tool, include_optional=include_optional_steps)
    for step_id in sequence:
        if execution.status in {"blocked", "waiting"}:
            break
        if step_id in execution.completed_step_ids:
            continue
        if step_id == "dc_final_notice":
            _finalize_running_route_if_needed(repository, execution, workflow_tool)
            final_notice(repository, execution)
            continue
        progress_started(repository, execution, step_id)
        run_database_creation_step(runtime, repository, execution, step_id)
    if execution.status == "running":
        _finalize_running_route_if_needed(repository, execution, workflow_tool)
        final_notice(repository, execution)
    elif execution.status == "blocked":
        final_notice(repository, execution)
    return execution


def _finalize_running_route_if_needed(repository, execution: DatabaseCreationExecution, workflow_tool: str) -> None:
    if execution.status != "running":
        return
    execution.final_state = final_state_for_completed_route(workflow_tool, execution.final_state)
    if execution.final_state == "no_semantic_release" and execution.target is not None:
        build_and_store_resume(
            repository,
            execution,
            next_step_id="branch_select_default_or_custom_semantic_release",
        )
