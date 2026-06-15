from __future__ import annotations

from semantic_control_kernel.workflows.database_creation.route_resume import (
    build_and_store_resume,
    next_missing_step,
    write_incomplete_marker_if_possible,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    complete_step,
)
from semantic_control_kernel.workflows.database_creation.step_support import missing_target_blocker, stop_step


def step_persist_incomplete_state(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    if execution.target is None:
        stop_step(repository, execution, missing_target_blocker("rel_persist_incomplete_state"))
        return
    resume_context = build_and_store_resume(repository, execution, next_step_id=next_missing_step(execution))
    marker_path = write_incomplete_marker_if_possible(execution, resume_context)
    output = {
        "resume_context": resume_context.to_dict(),
        "incomplete_marker_path": marker_path,
    }
    complete_step(
        repository,
        execution,
        step_id="rel_persist_incomplete_state",
        function_name="persist_incomplete_semantic_release_state",
        final_state="semantic_release_incomplete",
        output_refs=[output],
    )
