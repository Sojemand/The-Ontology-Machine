from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.workflows.database_creation.semantic_adapter_calls import call_semantic_adapter
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import release_package_path
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
)


def step_create_custom_release(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    staged_taxonomy = execution.artifacts.get("staged_taxonomy_ref")
    staged_projection = execution.artifacts.get("staged_projection_ref")
    if execution.target is None or not isinstance(staged_taxonomy, Mapping) or not isinstance(staged_projection, Mapping):
        stop_step(repository, execution, release_missing_blocker("rel_create_custom_release"))
        return
    blocker = transition_blocker(execution, "rel_create_custom_release", "create_custom_semantic_release")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    result = call_semantic_adapter(
        runtime.semantic_release_adapter,
        ("create_custom_semantic_release",),
        {
            "staged_taxonomy_ref": dict(staged_taxonomy),
            "staged_projection_ref": dict(staged_projection),
            "taxonomy_ref": dict(execution.artifacts.get("taxonomy_ref", {})),
            "semantic_release_folder": execution.target.semantic_release_path,
            "semantic_release_path": execution.target.semantic_release_path,
            "target_identity": execution.target_identity,
            "workflow_run_id": execution.workflow_run_id,
        },
        step_id="rel_create_custom_release",
        function_name="create_custom_semantic_release",
    )
    blocker = blocker_from_adapter_result("rel_create_custom_release", result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    custom_release = adapter_output(result)
    execution.artifacts["custom_release_candidate_ref"] = custom_release
    execution.artifacts["custom_release_ref"] = release_ref_from_custom_release_output(custom_release)
    complete_step(
        repository,
        execution,
        step_id="rel_create_custom_release",
        function_name="create_custom_semantic_release",
        output_refs=[custom_release],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )


def step_write_custom_release(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    release_ref = execution.artifacts.get("custom_release_ref")
    if execution.target is None or not isinstance(release_ref, Mapping):
        stop_step(repository, execution, release_missing_blocker("rel_write_custom_release"))
        return
    blocker = transition_blocker(
        execution,
        "rel_write_custom_release",
        "write_semantic_release",
        semantic_state="semantic_release_incomplete",
    )
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    release_id = str(release_ref.get("release_id", f"{execution.workflow_run_id}_custom_release"))
    release_path = release_package_path(execution.target, release_id)
    result = runtime.semantic_release_adapter.write_semantic_release(
        {
            "release_ref": dict(release_ref),
            "release_path": release_path,
            "base_release_path": str(execution.artifacts.get("default_release_path") or ""),
            "projection_update_state": dict(execution.artifacts.get("projection_update_state", {})),
            "staged_projection_ref": dict(execution.artifacts.get("staged_projection_ref", {})),
            "semantic_release_path": execution.target.semantic_release_path,
            "target_identity": execution.target.target_identity,
            "workflow_run_id": execution.workflow_run_id,
        }
    )
    blocker = blocker_from_adapter_result("rel_write_custom_release", result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    output = adapter_output(result)
    written_release_ref = output.get("release_ref")
    if isinstance(written_release_ref, Mapping):
        release_ref = dict(written_release_ref)
        execution.artifacts["custom_release_ref"] = release_ref
        release_id = str(release_ref.get("release_id") or release_id)
    release_path = str(output.get("release_path") or release_path)
    execution.artifacts["custom_release_path"] = release_path
    complete_step(
        repository,
        execution,
        step_id="rel_write_custom_release",
        function_name="write_semantic_release",
        output_refs=[{"release_path": release_path, "release_id": release_id}],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )


def release_ref_from_custom_release_output(output: Mapping[str, Any]) -> dict[str, Any]:
    nested = output.get("release_ref")
    if isinstance(nested, Mapping):
        return dict(nested)
    return dict(output)
