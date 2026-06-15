from __future__ import annotations

from typing import TYPE_CHECKING

from semantic_control_kernel.repository.errors import BindingConflictError, BindingNotFoundError
from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.workflows.database_creation.provisioning_runner import run_or_block
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    adapter_output,
    complete_step,
    create_blocker,
)
from semantic_control_kernel.workflows.database_creation.step_support import (
    adapter_receipt_ref,
    blocker_from_adapter_result,
    missing_target_blocker,
    transition_blocker,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.routes import DatabaseCreationRuntime


def create_and_bind_empty_database(
    runtime: "DatabaseCreationRuntime",
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
) -> DatabaseCreationBlocker | None:
    if execution.target is None:
        return missing_target_blocker("dc_create_empty_database")
    preexisting_binding = _binding_conflict_blocker_for_target(repository, execution)
    if preexisting_binding is not None:
        return preexisting_binding
    blocker = transition_blocker(execution, "dc_create_empty_database", "create_empty_database")
    if blocker is not None:
        return blocker
    result = runtime.corpus_adapter.create_empty_database(
        {
            "database_path": execution.target.database_path,
            "corpus_path": execution.target.corpus_path,
            "database_name": execution.target.database_name,
            "target_identity": execution.target.target_identity,
        }
    )
    blocker = blocker_from_adapter_result("dc_create_empty_database", result)
    if blocker is not None:
        return blocker
    output = adapter_output(result)
    database_id = str(
        output.get("database_id")
        or output.get("database_path_hash")
        or execution.target.path_hashes["database_path_hash"]
    )
    receipt = complete_step(
        repository,
        execution,
        step_id="dc_create_empty_database",
        function_name="create_empty_database",
        final_state="no_semantic_release",
        output_refs=[{"database_path": execution.target.database_path, "database_id": database_id}],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )
    return _store_binding_or_block(
        repository,
        execution,
        database_id=database_id,
        evidence_refs=[str(receipt.payload["operation_receipt_id"])],
    )


def _binding_conflict_blocker_for_target(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
) -> DatabaseCreationBlocker | None:
    target = execution.target
    if target is None:
        return None
    try:
        repository.bindings.get_by_database_path(target.database_path)
    except BindingNotFoundError:
        pass
    else:
        return _binding_conflict_blocker("database path")
    try:
        repository.bindings.get_by_artifact_root(target.artifact_root_path)
    except BindingNotFoundError:
        return None
    return _binding_conflict_blocker("Artifact Tree root")


def _binding_conflict_blocker(target_name: str) -> DatabaseCreationBlocker:
    return create_blocker(
        step_id="dc_create_empty_database",
        function_or_route="create_empty_database",
        blocker_code="binding_conflict",
        recovery_state_class="broken_database_artifact_binding",
        summary=f"An active database/artifact binding already exists for the selected {target_name}.",
    )


def _store_binding_or_block(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    *,
    database_id: str,
    evidence_refs: list[str],
) -> DatabaseCreationBlocker | None:
    try:
        repository.store_database_binding(
            execution,
            database_id=database_id,
            evidence_refs=evidence_refs,
        )
    except BindingConflictError as exc:
        return create_blocker(
            step_id="dc_create_empty_database",
            function_or_route="create_empty_database",
            blocker_code="binding_conflict",
            recovery_state_class="broken_database_artifact_binding",
            summary=str(exc),
        )
    return None


def step_create_empty_database(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    run_or_block(runtime, repository, execution, create_and_bind_empty_database, final_state="no_semantic_release")
