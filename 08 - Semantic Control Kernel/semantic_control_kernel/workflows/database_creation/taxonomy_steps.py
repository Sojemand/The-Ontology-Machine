from __future__ import annotations

from collections.abc import Mapping
from semantic_control_kernel.workflows.database_creation.custom_taxonomy import (
    run_taxonomy_llm_path,
    validate_taxonomy_samples,
)
from semantic_control_kernel.workflows.database_creation.route_llm import (
    complete_llm_bundle,
    emit_analysis_report_mirror,
    progress_llm_port,
)
from semantic_control_kernel.workflows.database_creation.route_state import creation_analysis_artifact_root
from semantic_control_kernel.workflows.database_creation.sample_waiting import (
    pending_sample_request,
    wait_for_sample_files,
)
from semantic_control_kernel.workflows.database_creation.semantic_adapter_calls import call_semantic_adapter
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import (
    enriched_taxonomy_ref,
    staged_component_from_adapter_output,
)
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


def step_tax_require_samples(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    sample_refs = tuple(execution.artifacts.get("taxonomy_sample_refs") or ())
    if not sample_refs:
        sample_refs = runtime.interaction_port.select_sample_files(
            workflow_tool=execution.workflow_tool,
            workflow_run_id=execution.workflow_run_id,
            purpose="taxonomy",
            target=execution.target,
        )
    if not sample_refs and pending_sample_request(runtime, execution.workflow_run_id) is not None:
        wait_for_sample_files(
            runtime,
            repository,
            execution,
            step_id="tax_require_samples",
            fallback_summary="The Kernel is waiting for taxonomy sample files.",
        )
        return
    blocker = validate_taxonomy_samples(target=execution.target, sample_refs=sample_refs)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    execution.artifacts["taxonomy_sample_refs"] = [dict(item) for item in sample_refs]
    complete_step(
        repository,
        execution,
        step_id="tax_require_samples",
        function_name="require_sample_files_for_taxonomy_authoring",
        output_refs=[{"sample_refs": [dict(item) for item in sample_refs]}],
    )


def step_taxonomy_llm_path(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    sample_refs = tuple(execution.artifacts.get("taxonomy_sample_refs") or ())
    artifact_root = creation_analysis_artifact_root(runtime, execution)
    update_state, blocker, operations, reports = run_taxonomy_llm_path(
        progress_llm_port(runtime.llm_port, repository, execution, step_id_prefix="llm_taxonomy"),
        workflow_run_id=execution.workflow_run_id,
        artifact_root=artifact_root,
        sample_refs=sample_refs,
        target=execution.target,
        runtime_settings=runtime.runtime_settings,
    )
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    execution.artifacts["taxonomy_update_state"] = update_state
    complete_llm_bundle(
        repository,
        execution,
        ("tax_analyze_samples", "tax_create_proposal", "tax_build_update_state"),
        tuple(operations),
        update_state,
    )
    for report, analysis_run_id in reports:
        emit_analysis_report_mirror(
            repository,
            execution,
            report_function=report.report_function,
            report_text=report.report_text,
            analysis_run_id=analysis_run_id,
            unavailable_detail=report.unavailable_detail,
        )


def step_create_custom_taxonomy(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    update_state = execution.artifacts.get("taxonomy_update_state")
    if not isinstance(update_state, Mapping):
        stop_step(repository, execution, update_state_missing_blocker("tax_create_custom_taxonomy"))
        return
    blocker = transition_blocker(execution, "tax_create_custom_taxonomy", "create_custom_taxonomy")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    result = call_semantic_adapter(
        runtime.semantic_release_adapter,
        ("create_custom_taxonomy", "stage_taxonomy"),
        {
            "update_state": dict(update_state),
            "target_identity": execution.target_identity,
        },
        step_id="tax_create_custom_taxonomy",
        function_name="create_custom_taxonomy",
    )
    blocker = blocker_from_adapter_result("tax_create_custom_taxonomy", result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    output = adapter_output(result)
    execution.artifacts["custom_taxonomy"] = output
    complete_step(
        repository,
        execution,
        step_id="tax_create_custom_taxonomy",
        function_name="create_custom_taxonomy",
        output_refs=[output],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )


def step_stage_custom_taxonomy(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    custom_taxonomy = execution.artifacts.get("custom_taxonomy")
    update_state = execution.artifacts.get("taxonomy_update_state")
    if not isinstance(custom_taxonomy, Mapping):
        stop_step(repository, execution, release_missing_blocker("tax_stage_custom_taxonomy"))
        return
    if not isinstance(update_state, Mapping):
        stop_step(repository, execution, update_state_missing_blocker("tax_stage_custom_taxonomy"))
        return
    blocker = transition_blocker(execution, "tax_stage_custom_taxonomy", "stage_custom_taxonomy_for_semantic_release")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    result = call_semantic_adapter(
        runtime.semantic_release_adapter,
        ("stage_taxonomy",),
        {
            "custom_taxonomy": dict(custom_taxonomy),
            "update_state": dict(update_state),
            "semantic_release_path": execution.target.semantic_release_path if execution.target else "",
            "target_identity": execution.target_identity,
        },
        step_id="tax_stage_custom_taxonomy",
        function_name="stage_custom_taxonomy_for_semantic_release",
    )
    blocker = blocker_from_adapter_result("tax_stage_custom_taxonomy", result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    staged = staged_component_from_adapter_output(
        component_kind="taxonomy",
        output=adapter_output(result),
        fallback_stage_id=f"{execution.workflow_run_id}_taxonomy_stage",
        source_analysis_refs=[dict(update_state)],
    ).to_dict()
    execution.artifacts["staged_taxonomy_ref"] = staged
    execution.artifacts["taxonomy_ref"] = enriched_taxonomy_ref(
        staged["component_identity"],
        update_state=update_state,
        source="staged",
    )
    complete_step(
        repository,
        execution,
        step_id="tax_stage_custom_taxonomy",
        function_name="stage_custom_taxonomy_for_semantic_release",
        final_state="semantic_release_incomplete",
        output_refs=[staged],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )
