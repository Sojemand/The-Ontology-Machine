from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.workflows.database_creation.route_state import default_release_ref
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import (
    projectionless_release_state_payload,
    release_package_path,
    write_projectionless_release_state,
)
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
    release_missing_blocker,
    stop_step,
    transition_blocker,
)


def step_remove_default_projections(runtime, repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    release_ref = default_release_ref(execution)
    if execution.target is None or release_ref is None:
        stop_step(repository, execution, release_missing_blocker("dc_remove_default_projections"))
        return
    blocker = transition_blocker(
        execution,
        "dc_remove_default_projections",
        "remove_projection_from_database",
        confirmation_ref="phase9_projectionless_route_confirmation",
    )
    if blocker is not None:
        stop_step(repository, execution, blocker)
        return
    adapter_receipts: list[Mapping[str, Any]] = []
    removed_projection_refs: list[Mapping[str, Any]] = []
    current_release_ref: dict[str, Any] = release_ref.to_dict()
    release_path = str(execution.artifacts.get("default_release_path") or release_package_path(execution.target, release_ref.release_id))
    for projection_ref in release_ref.projection_refs:
        result = runtime.semantic_release_adapter.remove_taxonomy_or_projection(
            {
                "component_kind": "projection",
                "release_ref": current_release_ref,
                "release_path": release_path,
                "semantic_release_path": execution.target.semantic_release_path,
                "corpus_db_path": execution.target.database_path,
                "projection_ref": dict(projection_ref),
                "target_identity": execution.target.target_identity,
                "route_confirmation": "phase9_projectionless_route_confirmation",
                "confirmation_receipt_ref": {
                    "confirmation_request_id": "phase9_projectionless_route_confirmation",
                    "confirmed_target_identity": execution.target.target_identity,
                },
            }
        )
        blocker = blocker_from_adapter_result("dc_remove_default_projections", result)
        if blocker is not None:
            stop_step(repository, execution, blocker)
            return
        output = adapter_output(result)
        updated_release_ref = output.get("updated_release_ref")
        if not isinstance(updated_release_ref, Mapping):
            stop_step(
                repository,
                execution,
                create_blocker(
                    step_id="dc_remove_default_projections",
                    function_or_route="remove_projection_from_database",
                    blocker_code="release_incomplete",
                    recovery_state_class="semantic_release_incomplete_staged",
                    summary="Projection removal did not return an updated projectionless release reference.",
                ),
            )
            return
        current_release_ref = dict(updated_release_ref)
        removed = output.get("removed_projection_refs")
        if isinstance(removed, list):
            removed_projection_refs.extend(dict(item) for item in removed if isinstance(item, Mapping))
        else:
            removed_projection_refs.append(dict(projection_ref))
        adapter_receipts.append(adapter_receipt_ref(result))
    projectionless_release_ref = dict(current_release_ref)
    taxonomy_ref = projectionless_release_ref.get("taxonomy_ref")
    remaining_projection_refs = projectionless_release_ref.get("projection_refs")
    if not isinstance(taxonomy_ref, Mapping) or not isinstance(remaining_projection_refs, list) or remaining_projection_refs:
        stop_step(
            repository,
            execution,
            create_blocker(
                step_id="dc_remove_default_projections",
                function_or_route="remove_projection_from_database",
                blocker_code="release_incomplete",
                recovery_state_class="semantic_release_incomplete_staged",
                summary="Projection removal did not leave a validated taxonomy-only release reference.",
            ),
        )
        return
    projectionless_payload = projectionless_release_state_payload(
        target=execution.target,
        workflow_run_id=execution.workflow_run_id,
        workflow_tool=execution.workflow_tool,
        source_default_release_ref=release_ref.to_dict(),
        projectionless_release_ref=projectionless_release_ref,
        taxonomy_ref=taxonomy_ref,
        removed_projection_refs=removed_projection_refs,
        adapter_receipt_refs=adapter_receipts,
    )
    projectionless_state_path = write_projectionless_release_state(
        target=execution.target,
        payload=projectionless_payload,
    )
    projectionless_state_ref = {
        "schema_version": "kernel.default_taxonomy_projectionless_release_state.ref.v1",
        "artifact_path": projectionless_state_path,
        "release_id": str(projectionless_release_ref.get("release_id") or release_ref.release_id),
        "release_fingerprint": str(projectionless_release_ref.get("release_fingerprint") or ""),
        "missing_component_type": "projections",
        "completeness_state": "incomplete",
    }
    execution.artifacts["default_projection_refs"] = []
    execution.artifacts["projectionless_release_ref"] = projectionless_release_ref
    execution.artifacts["projectionless_release_state_ref"] = projectionless_state_ref
    execution.artifacts["projectionless_release_state_path"] = projectionless_state_path
    execution.artifacts["removed_default_projection_refs"] = [dict(item) for item in removed_projection_refs]
    execution.artifacts["staged_taxonomy_ref"] = {
        "component_kind": "taxonomy",
        "stage_id": "default_taxonomy_without_projections",
        "artifact_ref": {"artifact_path": projectionless_state_path, "release_path": release_path},
        "component_identity": dict(taxonomy_ref),
        "fingerprint": str(
            taxonomy_ref.get("taxonomy_fingerprint")
            or projectionless_release_ref.get("release_fingerprint")
            or release_ref.release_fingerprint
        ),
        "source_analysis_refs": [],
        "validation_status": "validated",
    }
    receipt = complete_step(
        repository,
        execution,
        step_id="dc_remove_default_projections",
        function_name="remove_projection_from_database",
        final_state="semantic_release_incomplete",
        output_refs=[
            execution.artifacts["staged_taxonomy_ref"],
            projectionless_state_ref,
        ],
        pipeline_adapter_receipts=adapter_receipts,
    )
    repository.attach_states.clear_attach_state(
        execution.target.target_identity,
        str(receipt.payload["operation_receipt_id"]),
    )
    execution.artifacts["default_attach_state_archived_after_projection_strip"] = True
