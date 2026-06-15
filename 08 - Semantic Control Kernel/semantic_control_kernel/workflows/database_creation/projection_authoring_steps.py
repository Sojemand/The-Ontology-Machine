from __future__ import annotations

from collections.abc import Mapping
from semantic_control_kernel.workflows.database_creation.custom_projection import (
    build_taxonomy_projection_authoring_view,
    run_projection_llm_path,
    taxonomy_ref_for_projection_authoring,
)
from semantic_control_kernel.workflows.database_creation.route_llm import (
    complete_llm_bundle,
    emit_analysis_report_mirror,
    progress_llm_port,
)
from semantic_control_kernel.workflows.database_creation.route_state import (
    creation_analysis_artifact_root,
    taxonomy_authoring_release_path,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    complete_step,
)
from semantic_control_kernel.workflows.database_creation.step_support import release_missing_blocker, stop_step


def step_projection_authoring_view(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    taxonomy_ref = execution.artifacts.get("taxonomy_ref")
    if not isinstance(taxonomy_ref, Mapping):
        stop_step(repository, execution, release_missing_blocker("proj_build_authoring_view"))
        return
    artifact_root = creation_analysis_artifact_root(runtime, execution)
    analysis_run_id = f"{execution.workflow_run_id}_projection"
    taxonomy_ref = taxonomy_ref_for_projection_authoring(
        taxonomy_ref,
        release_path=taxonomy_authoring_release_path(execution),
    )
    authoring_view = build_taxonomy_projection_authoring_view(
        taxonomy_ref,
        artifact_root=artifact_root,
        analysis_run_id=analysis_run_id,
        sample_scope={"sample_refs": execution.artifacts.get("projection_sample_refs", [])},
    )
    execution.artifacts["taxonomy_ref"] = taxonomy_ref
    execution.artifacts["taxonomy_authoring_view"] = authoring_view
    complete_step(
        repository,
        execution,
        step_id="proj_build_authoring_view",
        function_name="build_taxonomy_projection_authoring_view",
        output_refs=[authoring_view],
    )


def step_projection_llm_path(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    taxonomy_ref = execution.artifacts.get("taxonomy_ref")
    authoring_view = execution.artifacts.get("taxonomy_authoring_view")
    if not isinstance(taxonomy_ref, Mapping) or not isinstance(authoring_view, Mapping):
        stop_step(repository, execution, release_missing_blocker("proj_analyze_samples"))
        return
    artifact_root = creation_analysis_artifact_root(runtime, execution)
    update_state, blocker, operations, reports = run_projection_llm_path(
        progress_llm_port(runtime.llm_port, repository, execution, step_id_prefix="llm_projection"),
        workflow_run_id=execution.workflow_run_id,
        artifact_root=artifact_root,
        sample_refs=tuple(execution.artifacts.get("projection_sample_refs") or ()),
        taxonomy_ref=taxonomy_ref,
        taxonomy_authoring_view=authoring_view,
        target=execution.target,
        runtime_settings=runtime.runtime_settings,
    )
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    execution.artifacts["projection_update_state"] = update_state
    complete_llm_bundle(
        repository,
        execution,
        ("proj_analyze_samples", "proj_create_proposal", "proj_build_update_state"),
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
