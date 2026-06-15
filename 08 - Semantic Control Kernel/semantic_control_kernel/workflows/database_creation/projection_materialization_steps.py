from __future__ import annotations

from collections.abc import Mapping

from semantic_control_kernel.types.adapter_results import AdapterCallResult
from semantic_control_kernel.workflows.database_creation.custom_projection import projection_validation_blocker
from semantic_control_kernel.workflows.database_creation.semantic_adapter_calls import call_semantic_adapter
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import staged_component_from_adapter_output
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    adapter_output,
    complete_step,
)
from semantic_control_kernel.workflows.database_creation.step_support import (
    adapter_receipt_ref,
    blocker_from_adapter_result,
    release_missing_blocker,
    stop_step,
    transition_blocker,
    update_state_missing_blocker,
)


def step_create_custom_projection(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    update_state = execution.artifacts.get("projection_update_state")
    if not isinstance(update_state, Mapping):
        stop_step(repository, execution, update_state_missing_blocker("proj_create_custom_projection"))
        return
    blocker = transition_blocker(execution, "proj_create_custom_projection", "create_custom_projection")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    result = call_semantic_adapter(
        runtime.semantic_release_adapter,
        ("create_custom_projection", "stage_projections"),
        {
            "update_state": dict(update_state),
            "taxonomy_ref": dict(execution.artifacts.get("taxonomy_ref", {})),
            "target_identity": execution.target_identity,
        },
        step_id="proj_create_custom_projection",
        function_name="create_custom_projection",
    )
    blocker = blocker_from_adapter_result("proj_create_custom_projection", result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    output = adapter_output(result)
    execution.artifacts["custom_projection"] = output
    complete_step(
        repository,
        execution,
        step_id="proj_create_custom_projection",
        function_name="create_custom_projection",
        output_refs=[output],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )


def step_validate_custom_projection(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    custom_projection = execution.artifacts.get("custom_projection")
    taxonomy_ref = execution.artifacts.get("taxonomy_ref")
    if not isinstance(custom_projection, Mapping) or not isinstance(taxonomy_ref, Mapping):
        stop_step(repository, execution, release_missing_blocker("proj_validate_projection"))
        return
    blocker = transition_blocker(execution, "proj_validate_projection", "validate_projections_against_taxonomy")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    result = call_semantic_adapter(
        runtime.semantic_release_adapter,
        ("validate_projections_against_taxonomy", "validate_projection_binding"),
        {
            "custom_projection": dict(custom_projection),
            "taxonomy_ref": dict(taxonomy_ref),
            "target_identity": execution.target_identity,
        },
        step_id="proj_validate_projection",
        function_name="validate_projections_against_taxonomy",
    )
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        stop_step(repository, execution, projection_validation_blocker("proj_validate_projection", "Custom projections failed taxonomy validation."))
        return
    blocker = blocker_from_adapter_result("proj_validate_projection", result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    validation = adapter_output(result)
    if validation.get("validation_status") == "invalid":
        stop_step(
            repository,
            execution,
            projection_validation_blocker(
                "proj_validate_projection",
                str(validation.get("summary", "Projection taxonomy validation failed.")),
            ),
        )
        return
    execution.artifacts["projection_validation"] = validation or {"validation_status": "validated"}
    complete_step(
        repository,
        execution,
        step_id="proj_validate_projection",
        function_name="validate_projections_against_taxonomy",
        output_refs=[execution.artifacts["projection_validation"]],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )


def step_stage_custom_projection(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    custom_projection = execution.artifacts.get("custom_projection")
    update_state = execution.artifacts.get("projection_update_state")
    if not isinstance(custom_projection, Mapping) or not isinstance(update_state, Mapping):
        stop_step(repository, execution, release_missing_blocker("proj_stage_custom_projection"))
        return
    blocker = transition_blocker(execution, "proj_stage_custom_projection", "stage_custom_projections_for_semantic_release")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    result = call_semantic_adapter(
        runtime.semantic_release_adapter,
        ("stage_projections",),
        {
            "custom_projection": dict(custom_projection),
            "update_state": dict(update_state),
            "projection_validation": dict(execution.artifacts.get("projection_validation", {})),
            "taxonomy_ref": dict(execution.artifacts.get("taxonomy_ref", {})),
            "semantic_release_path": execution.target.semantic_release_path if execution.target else "",
            "target_identity": execution.target_identity,
        },
        step_id="proj_stage_custom_projection",
        function_name="stage_custom_projections_for_semantic_release",
    )
    blocker = blocker_from_adapter_result("proj_stage_custom_projection", result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    staged = staged_component_from_adapter_output(
        component_kind="projections",
        output=adapter_output(result),
        fallback_stage_id=f"{execution.workflow_run_id}_projection_stage",
        source_analysis_refs=[dict(execution.artifacts.get("projection_update_state", {}))],
    ).to_dict()
    execution.artifacts["staged_projection_ref"] = staged
    complete_step(
        repository,
        execution,
        step_id="proj_stage_custom_projection",
        function_name="stage_custom_projections_for_semantic_release",
        final_state="semantic_release_incomplete",
        output_refs=[staged],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )
