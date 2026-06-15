from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.evaluator import StateMachineEvaluator
from semantic_control_kernel.domain.state_machine.models import EligibilityStatus, TransitionInputRefs
from semantic_control_kernel.domain.state_machine.transition_table import get_transition_rule
from semantic_control_kernel.types.adapter_results import AdapterCallResult
from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.workflows.database_creation.route_sequences import get_step
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    blocker_from_missing_capability,
    create_blocker,
    is_missing_capability,
)


JsonObject = dict[str, Any]


def stop_step(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    blocker: DatabaseCreationBlocker,
    *,
    final_state: str | None = None,
) -> None:
    from semantic_control_kernel.workflows.database_creation.route_resume import block_database_creation

    block_database_creation(repository, execution, blocker, final_state=final_state or execution.final_state)


def missing_target_blocker(step_id: str) -> DatabaseCreationBlocker:
    return create_blocker(
        step_id=step_id,
        function_or_route="create_standard_artifact_folder_tree",
        blocker_code="input_missing",
        recovery_state_class="expired_pending_interaction",
        summary="Database creation target is missing from Kernel workflow state.",
    )


def transition_blocker(
    execution: DatabaseCreationExecution,
    step_id: str,
    function_or_route: str,
    *,
    semantic_state: str | None = None,
    confirmation_ref: str | None = None,
) -> DatabaseCreationBlocker | None:
    rule = get_transition_rule(function_or_route)
    confirmation_receipts: dict[str, Mapping[str, Any]] = {}
    if confirmation_ref is not None:
        confirmation_receipts[confirmation_ref] = {
            "schema_version": "kernel.confirmation_receipt.v1",
            "confirmation_receipt_id": f"{confirmation_ref}_receipt",
            "confirmation_request_id": confirmation_ref,
            "confirmed_at": "",
            "confirmed_state_snapshot_identity": {
                "schema_version": "state.snapshot_identity.v1",
                "state_snapshot_id": execution.state_snapshot_id,
            },
            "confirmed_target_identity": execution.target_identity,
            "explanation_hash": "",
            "host_surface_identity": "database_creation_workflow",
            "user_decision": "confirmed",
        }
    result = StateMachineEvaluator().evaluate(
        function_or_route,
        active_state(execution, semantic_state=semantic_state),
        TransitionInputRefs.for_rule(rule, confirmation_receipts=confirmation_receipts),
        confirmation_ref=confirmation_ref,
    )
    if result.status == EligibilityStatus.ALLOWED.value:
        return None
    if result.status == EligibilityStatus.CONFIRMATION_REQUIRED.value:
        code = "confirmation_missing"
        summary = f"{function_or_route} requires {result.required_confirmation_gate} confirmation."
        recovery = "expired_pending_interaction"
    elif result.blockers:
        blocker = result.blockers[0]
        return create_blocker(
            step_id=step_id,
            function_or_route=function_or_route,
            blocker_code=blocker.blocker_code,
            recovery_state_class=blocker.recovery_state_class,
            summary=blocker.user_visible_summary,
            diagnostics=[blocker.to_dict()],
        )
    else:
        code = "missing_required_state"
        summary = f"{function_or_route} is not eligible from current Kernel state."
        recovery = "semantic_release_incomplete_staged"
    return create_blocker(
        step_id=step_id,
        function_or_route=function_or_route,
        blocker_code=code,
        recovery_state_class=recovery,
        summary=summary,
    )


def active_state(execution: DatabaseCreationExecution, *, semantic_state: str | None = None) -> JsonObject:
    state = semantic_state or execution.final_state
    known_existing_target = execution.target is not None and state in {
        "no_semantic_release",
        "semantic_release_incomplete",
        "semantic_release_complete_not_active",
        "semantic_release_active",
    }
    artifact_exists = (
        "dc_store_artifact_tree" in execution.completed_step_ids
        or "dc_create_artifact_tree" in execution.completed_step_ids
        or known_existing_target
    )
    database_exists = "dc_create_empty_database" in execution.completed_step_ids or known_existing_target
    target_identity = execution.target_identity
    return {
        "schema_version": "kernel.active_database_state.v1",
        "state_snapshot_id": execution.state_snapshot_id,
        "artifact_tree": {"exists": artifact_exists, "target_identity": target_identity},
        "active_database": {"database_exists": database_exists, "target_identity": target_identity},
        "database_emptiness": "empty" if database_exists else "unknown",
        "semantic_release_state": state,
        "blocking_reasons": [],
        "active_lock_refs": [],
        "evidence_refs": [],
    }


def blocker_from_adapter_result(step_id: str, result: object) -> DatabaseCreationBlocker | None:
    if isinstance(result, DatabaseCreationBlocker):
        return result
    if is_missing_capability(result):
        return blocker_from_missing_capability(step_id, result)  # type: ignore[arg-type]
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return create_blocker(
            step_id=step_id,
            function_or_route=str(result.to_dict().get("kernel_function", step_id)),
            blocker_code=str(result.to_dict().get("status", "owner_error")),
            recovery_state_class="support_only_unrecoverable",
            summary=f"Pipeline adapter returned {result.status}.",
            diagnostics=result.to_dict().get("diagnostics", ()),
        )
    if result is None:
        return create_blocker(
            step_id=step_id,
            function_or_route=step_id,
            blocker_code="invalid_owner_response",
            recovery_state_class="support_only_unrecoverable",
            summary="Pipeline adapter returned no result.",
        )
    return None


def adapter_receipt_ref(result: object) -> Mapping[str, Any]:
    if isinstance(result, AdapterCallResult):
        payload = result.to_dict()
        return {
            "adapter_call_id": payload.get("adapter_call_id", ""),
            "adapter_name": payload.get("adapter_name", ""),
            "status": payload.get("status", ""),
        }
    if is_missing_capability(result):
        return result.to_dict()  # type: ignore[return-value]
    if isinstance(result, Mapping):
        return dict(result)
    return {}


def release_missing_blocker(step_id: str) -> DatabaseCreationBlocker:
    return create_blocker(
        step_id=step_id,
        function_or_route=get_step(step_id).operation,
        blocker_code="release_missing",
        recovery_state_class="semantic_release_incomplete_staged",
        summary="Required Semantic Release evidence is missing from Kernel workflow state.",
    )


def update_state_missing_blocker(step_id: str) -> DatabaseCreationBlocker:
    return create_blocker(
        step_id=step_id,
        function_or_route=get_step(step_id).operation,
        blocker_code="update_state_invalid",
        recovery_state_class="final_llm_validation_failure",
        summary="Required creation update-state is missing from Kernel workflow state.",
    )
