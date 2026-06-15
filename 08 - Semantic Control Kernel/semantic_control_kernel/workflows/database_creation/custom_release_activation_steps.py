from __future__ import annotations

from collections.abc import Mapping

from semantic_control_kernel.policy.runtime_locale import control_locale_or_default
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import release_package_path
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    complete_step,
)
from semantic_control_kernel.workflows.database_creation.step_support import (
    adapter_receipt_ref,
    blocker_from_adapter_result,
    release_missing_blocker,
    stop_step,
    transition_blocker,
)


def step_attach_custom_release(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    release_ref = execution.artifacts.get("custom_release_ref")
    if execution.target is None or not isinstance(release_ref, Mapping):
        stop_step(repository, execution, release_missing_blocker("rel_attach_custom_release"))
        return
    blocker = transition_blocker(execution, "rel_attach_custom_release", "attach_custom_semantic_release_to_database")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    release_path = str(
        execution.artifacts.get("custom_release_path")
        or release_package_path(execution.target, str(release_ref.get("release_id", "custom_release")))
    )
    load_result = runtime.semantic_release_adapter.load_semantic_release(
        {
            "release_ref": dict(release_ref),
            "release_path": release_path,
            "corpus_db_path": execution.target.database_path,
            "target_identity": execution.target.target_identity,
        }
    )
    blocker = blocker_from_adapter_result("rel_attach_custom_release", load_result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    preflight_result = runtime.semantic_release_adapter.preflight_semantic_release_activation(
        {
            "release_ref": dict(release_ref),
            "release_path": release_path,
            "corpus_db_path": execution.target.database_path,
            "target_identity": execution.target.target_identity,
        }
    )
    blocker = blocker_from_adapter_result("rel_attach_custom_release", preflight_result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    receipt = complete_step(
        repository,
        execution,
        step_id="rel_attach_custom_release",
        function_name="attach_custom_semantic_release_to_database",
        final_state="semantic_release_complete_not_active",
        output_refs=[{"release_path": release_path, "release_id": release_ref.get("release_id", "")}],
        pipeline_adapter_receipts=[adapter_receipt_ref(load_result), adapter_receipt_ref(preflight_result)],
    )
    repository.put_attach_state(
        execution,
        release_path=release_path,
        release_id=str(release_ref.get("release_id", "")),
        release_version=str(release_ref.get("release_version", "")),
        release_fingerprint=str(release_ref.get("release_fingerprint", "")),
        runtime_locale=control_locale_or_default(release_ref.get("runtime_locale")),
        attach_receipt_id=str(receipt.payload["operation_receipt_id"]),
    )


def step_activate_custom_release(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    release_ref = execution.artifacts.get("custom_release_ref")
    if execution.target is None or not isinstance(release_ref, Mapping):
        stop_step(repository, execution, release_missing_blocker("rel_activate_custom_release"))
        return
    blocker = transition_blocker(execution, "rel_activate_custom_release", "activate_semantic_release")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    release_path = str(
        execution.artifacts.get("custom_release_path")
        or release_package_path(execution.target, str(release_ref.get("release_id", "custom_release")))
    )
    preflight_result = runtime.semantic_release_adapter.preflight_semantic_release_activation(
        {
            "release_ref": dict(release_ref),
            "release_path": release_path,
            "corpus_db_path": execution.target.database_path,
            "target_identity": execution.target.target_identity,
        }
    )
    blocker = blocker_from_adapter_result("rel_activate_custom_release", preflight_result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    activate_result = runtime.semantic_release_adapter.activate_semantic_release(
        {
            "release_ref": dict(release_ref),
            "release_path": release_path,
            "corpus_db_path": execution.target.database_path,
            "target_identity": execution.target.target_identity,
        }
    )
    blocker = blocker_from_adapter_result("rel_activate_custom_release", activate_result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    complete_step(
        repository,
        execution,
        step_id="rel_activate_custom_release",
        function_name="activate_semantic_release",
        final_state="semantic_release_active",
        output_refs=[{"release_path": release_path, "release_id": release_ref.get("release_id", "")}],
        pipeline_adapter_receipts=[adapter_receipt_ref(preflight_result), adapter_receipt_ref(activate_result)],
    )
