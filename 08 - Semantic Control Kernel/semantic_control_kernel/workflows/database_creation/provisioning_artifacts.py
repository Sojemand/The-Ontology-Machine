from __future__ import annotations

from typing import TYPE_CHECKING

from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.workflows.database_creation.provisioning_runner import run_or_block
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    complete_step,
    create_blocker,
    reject_target_conflict,
    validate_artifact_tree_contract,
)
from semantic_control_kernel.workflows.database_creation.step_support import (
    adapter_receipt_ref,
    blocker_from_adapter_result,
    missing_target_blocker,
    transition_blocker,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.routes import DatabaseCreationRuntime


def prepare_artifact_tree_for_target(
    runtime: "DatabaseCreationRuntime",
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
) -> DatabaseCreationBlocker | None:
    if execution.target is None:
        return missing_target_blocker("dc_create_artifact_tree")
    conflict = reject_target_conflict(execution.target)
    if conflict is not None:
        return conflict
    blocker = transition_blocker(execution, "dc_create_artifact_tree", "create_standard_artifact_folder_tree")
    if blocker is not None:
        return blocker
    result = runtime.workspace_adapter.prepare_artifact_tree(
        {
            "target": execution.target.to_dict(),
            "canonical_folders": "phase9.database_creation.v1",
            "target_identity": execution.target.target_identity,
        }
    )
    blocker = blocker_from_adapter_result("dc_create_artifact_tree", result)
    if blocker is not None:
        return blocker
    complete_step(
        repository,
        execution,
        step_id="dc_create_artifact_tree",
        function_name="create_standard_artifact_folder_tree",
        output_refs=[{"artifact_root_path": execution.target.artifact_root_path}],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )
    return None


def verify_and_store_artifact_tree(
    runtime: "DatabaseCreationRuntime",
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
) -> DatabaseCreationBlocker | None:
    if execution.target is None:
        return missing_target_blocker("dc_store_artifact_tree")
    result = runtime.workspace_adapter.validate_artifact_tree(
        {
            "target": execution.target.to_dict(),
            "target_identity": execution.target.target_identity,
        }
    )
    blocker = blocker_from_adapter_result("dc_store_artifact_tree", result)
    if blocker is not None:
        return blocker
    ok, reason = validate_artifact_tree_contract(execution.target.artifact_root_path)
    if not ok:
        return create_blocker(
            step_id="dc_store_artifact_tree",
            function_or_route="store_active_artifact_folder_tree",
            blocker_code="missing_artifact_tree" if reason.startswith("missing") else "target_conflict",
            recovery_state_class="target_identity_changed",
            summary=f"Artifact Tree folder contract failed: {reason}.",
        )
    receipt = complete_step(
        repository,
        execution,
        step_id="dc_store_artifact_tree",
        function_name="store_active_artifact_folder_tree",
        output_refs=[execution.target.canonical_paths()],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )
    repository.store_active_artifact_tree(execution, str(receipt.payload["operation_receipt_id"]))
    return None


def step_create_artifact_tree(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    run_or_block(runtime, repository, execution, prepare_artifact_tree_for_target)


def step_store_artifact_tree(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    run_or_block(runtime, repository, execution, verify_and_store_artifact_tree)
