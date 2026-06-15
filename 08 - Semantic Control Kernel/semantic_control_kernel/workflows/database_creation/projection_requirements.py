from __future__ import annotations

from semantic_control_kernel.workflows.database_creation.custom_projection import (
    validate_projection_samples,
    validate_projection_taxonomy_ref,
)
from semantic_control_kernel.workflows.database_creation.route_state import resolve_taxonomy_ref
from semantic_control_kernel.workflows.database_creation.sample_waiting import (
    pending_sample_request,
    wait_for_sample_files,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    complete_step,
)
from semantic_control_kernel.workflows.database_creation.step_support import stop_step


def step_projection_require_taxonomy(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    taxonomy_ref = resolve_taxonomy_ref(runtime, execution)
    blocker = validate_projection_taxonomy_ref(taxonomy_ref)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    execution.artifacts["taxonomy_ref"] = dict(taxonomy_ref or {})
    complete_step(
        repository,
        execution,
        step_id="proj_require_taxonomy",
        function_name="resolve_taxonomy_for_projection_authoring",
        output_refs=[{"taxonomy_ref": dict(taxonomy_ref or {})}],
    )


def step_projection_require_samples(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    sample_refs = tuple(execution.artifacts.get("projection_sample_refs") or ())
    if not sample_refs:
        sample_refs = runtime.interaction_port.select_sample_files(
            workflow_tool=execution.workflow_tool,
            workflow_run_id=execution.workflow_run_id,
            purpose="projection",
            target=execution.target,
        )
    if not sample_refs and pending_sample_request(runtime, execution.workflow_run_id) is not None:
        wait_for_sample_files(
            runtime,
            repository,
            execution,
            step_id="proj_require_samples",
            fallback_summary="The Kernel is waiting for projection sample files.",
        )
        return
    blocker = validate_projection_samples(target=execution.target, sample_refs=sample_refs)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    execution.artifacts["projection_sample_refs"] = [dict(item) for item in sample_refs]
    complete_step(
        repository,
        execution,
        step_id="proj_require_samples",
        function_name="require_sample_files_for_projection_authoring",
        output_refs=[{"sample_refs": [dict(item) for item in sample_refs]}],
    )
