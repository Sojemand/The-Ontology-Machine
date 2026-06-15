from __future__ import annotations

from collections.abc import Mapping

from semantic_control_kernel.policy.runtime_locale import control_locale_or_default
from semantic_control_kernel.types.adapter_results import MissingCapabilityBlocker
from semantic_control_kernel.workflows.database_creation.default_release import (
    activate_release,
    export_default_release,
    load_default_release_for_attach,
    preflight_activation,
    validate_complete_default_release,
    write_default_release,
)
from semantic_control_kernel.workflows.database_creation.route_state import default_release_ref
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import release_package_path
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    adapter_output,
    blocker_from_missing_capability,
    complete_step,
)
from semantic_control_kernel.workflows.database_creation.step_support import (
    adapter_receipt_ref,
    blocker_from_adapter_result,
    missing_target_blocker,
    release_missing_blocker,
    stop_step,
    transition_blocker,
)


def step_export_default_release(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    if execution.target is None:
        stop_step(repository, execution, missing_target_blocker("dc_export_default_release"))
        return
    result = export_default_release(
        runtime.semantic_release_adapter,
        target=execution.target,
        blueprint_ref=runtime.blueprint_ref,
    )
    if isinstance(result, MissingCapabilityBlocker):
        stop_step(repository, execution, blocker_from_missing_capability("dc_export_default_release", result))
        return
    blocker = validate_complete_default_release(result)
    if blocker is not None:
        stop_step(repository, execution, blocker, final_state="semantic_release_incomplete")
        return
    execution.artifacts["default_release_ref"] = result.to_dict()
    release_export_path = result.source_adapter_receipt_ref.get("output_path") if isinstance(result.source_adapter_receipt_ref, Mapping) else ""
    if release_export_path:
        execution.artifacts["default_release_export_path"] = str(release_export_path)
    complete_step(
        repository,
        execution,
        step_id="dc_export_default_release",
        function_name="export_default_semantic_release",
        output_refs=[result.to_dict()],
    )


def step_write_default_release(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    release_ref = default_release_ref(execution)
    if execution.target is None or release_ref is None:
        stop_step(repository, execution, release_missing_blocker("dc_write_default_release"))
        return
    blocker = transition_blocker(
        execution,
        "dc_write_default_release",
        "write_semantic_release",
        semantic_state="semantic_release_incomplete",
    )
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    result = write_default_release(runtime.semantic_release_adapter, target=execution.target, release_ref=release_ref)
    blocker = blocker_from_adapter_result("dc_write_default_release", result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    release_path = str(adapter_output(result).get("release_path") or release_package_path(execution.target, release_ref.release_id))
    execution.artifacts["default_release_path"] = release_path
    complete_step(
        repository,
        execution,
        step_id="dc_write_default_release",
        function_name="write_semantic_release",
        output_refs=[{"release_path": release_path, "release_id": release_ref.release_id}],
        pipeline_adapter_receipts=[adapter_receipt_ref(result)],
    )


def step_attach_default_release(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    release_ref = default_release_ref(execution)
    if execution.target is None or release_ref is None:
        stop_step(repository, execution, release_missing_blocker("dc_attach_default_release"))
        return
    release_path = str(execution.artifacts.get("default_release_path") or release_package_path(execution.target, release_ref.release_id))
    blocker = transition_blocker(execution, "dc_attach_default_release", "attach_default_semantic_release_to_database")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    load_result = load_default_release_for_attach(
        runtime.semantic_release_adapter,
        target=execution.target,
        release_ref=release_ref,
        release_path=release_path,
    )
    blocker = blocker_from_adapter_result("dc_attach_default_release", load_result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    preflight_result = preflight_activation(
        runtime.semantic_release_adapter,
        target=execution.target,
        release_ref=release_ref,
        release_path=release_path,
    )
    blocker = blocker_from_adapter_result("dc_attach_default_release", preflight_result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    # This preflight proves the written package can be loaded before the Kernel
    # persists its attach pointer. Activation runs a second proof after that
    # state transition because owner-side runtime state may have changed.
    receipt = complete_step(
        repository,
        execution,
        step_id="dc_attach_default_release",
        function_name="attach_default_semantic_release_to_database",
        final_state="semantic_release_complete_not_active",
        output_refs=[{"release_path": release_path, "release_id": release_ref.release_id}],
        pipeline_adapter_receipts=[adapter_receipt_ref(load_result), adapter_receipt_ref(preflight_result)],
    )
    repository.put_attach_state(
        execution,
        release_path=release_path,
        release_id=release_ref.release_id,
        release_version=release_ref.release_version,
        release_fingerprint=release_ref.release_fingerprint,
        runtime_locale=control_locale_or_default(release_ref.taxonomy_ref.get("runtime_locale")),
        attach_receipt_id=str(receipt.payload["operation_receipt_id"]),
    )
    execution.artifacts["taxonomy_ref"] = dict(release_ref.taxonomy_ref)
    execution.artifacts["default_projection_refs"] = [dict(item) for item in release_ref.projection_refs]


def step_activate_default_release(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    release_ref = default_release_ref(execution)
    if execution.target is None or release_ref is None:
        stop_step(repository, execution, release_missing_blocker("dc_activate_default_release"))
        return
    release_path = str(execution.artifacts.get("default_release_path") or release_package_path(execution.target, release_ref.release_id))
    blocker = transition_blocker(execution, "dc_activate_default_release", "activate_semantic_release")
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    preflight_result = preflight_activation(runtime.semantic_release_adapter, target=execution.target, release_ref=release_ref, release_path=release_path)
    blocker = blocker_from_adapter_result("dc_activate_default_release", preflight_result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    execution.artifacts["default_activation_preflight_passed"] = True
    execution.artifacts["default_activation_owner_call_started"] = True
    activate_result = activate_release(runtime.semantic_release_adapter, target=execution.target, release_ref=release_ref, release_path=release_path)
    blocker = blocker_from_adapter_result("dc_activate_default_release", activate_result)
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    complete_step(
        repository,
        execution,
        step_id="dc_activate_default_release",
        function_name="activate_semantic_release",
        final_state="semantic_release_active",
        output_refs=[{"release_path": release_path, "release_id": release_ref.release_id}],
        pipeline_adapter_receipts=[adapter_receipt_ref(preflight_result), adapter_receipt_ref(activate_result)],
    )
