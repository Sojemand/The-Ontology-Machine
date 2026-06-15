from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.input_inventory import input_set_hash
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_helpers import (
    input_confirmation_identity,
    input_confirmation_request_id,
    input_state_snapshot_id,
    interaction_snapshot_id,
    manual_placeholder_identity,
    prefilled_values_for,
    restore_confirmation_identity,
)


def open_choose_artifact_root(
    user_interaction_service,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    progress,
) -> None:
    user_interaction_service.request_interaction(
        interaction_function="choose_artifact_root_folder",
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=manual_placeholder_identity(workflow_run_id),
        state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, "choose_artifact_root_folder")},
        user_visible_title="Choose Artifact Tree",
        user_visible_summary="Choose the Artifact Tree whose Input folder should be ingested into its active Corpus database.",
        prefilled_values=prefilled_values_for("choose_artifact_root_folder", progress),
    )


def open_name_database(
    user_interaction_service,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    artifact_root: str,
) -> None:
    user_interaction_service.request_interaction(
        interaction_function="name_database",
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=manual_placeholder_identity(workflow_run_id),
        state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, "name_database")},
        user_visible_title="Choose Corpus Database",
        user_visible_summary=f"Enter the Corpus database name inside {Path(artifact_root).name}.",
        prefilled_values={"text_value": Path(artifact_root).name},
    )


def open_input_confirmation(
    user_interaction_service,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    target: PipelineRunTarget,
    input_files: list[PipelineInputFile],
) -> None:
    user_interaction_service.request_interaction(
        interaction_function="select_sample_files",
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=input_confirmation_identity(target, input_files),
        state_snapshot_identity={"state_snapshot_id": input_state_snapshot_id(target, input_files)},
        user_visible_title="Confirm Input Files",
        user_visible_summary=(
            f"Confirm ingestion of {len(input_files)} file(s) from Input into {Path(target.database_path).name}."
        ),
        risk_class="long_running",
        confirmation_request_id=input_confirmation_request_id(target, input_files),
        prefilled_values={
            "artifact_root": target.artifact_root_path,
            "target_database_path": target.database_path,
            "input_file_count": len(input_files),
            "input_set_hash": input_set_hash(input_files),
        },
    )


def open_error_case_restore_confirmation(
    user_interaction_service,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    target: PipelineRunTarget,
    error_case_count: int,
    input_files_present: bool,
) -> None:
    summary = (
        f"{error_case_count} Error Case source file(s) exist. Confirm restore to Input before ingestion. "
        "Existing Input file(s) will be kept."
        if input_files_present
        else f"Input is empty and {error_case_count} Error Case source file(s) exist. Confirm restore to Input before ingestion."
    )
    user_interaction_service.request_interaction(
        interaction_function="user_confirmation",
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=restore_confirmation_identity(target, "error_cases"),
        state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, "restore_error_cases")},
        user_visible_title="Restore Error Cases",
        user_visible_summary=summary,
        risk_class="non_destructive",
        confirmation_request_id=f"manual_pipeline_run.restore_error_cases:{workflow_run_id}:{target.artifact_root_path_hash}",
        prefilled_values={"artifact_root": target.artifact_root_path, "error_case_file_count": error_case_count},
    )
