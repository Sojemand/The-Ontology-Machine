from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from semantic_control_kernel.types.enums import DialogType, InteractionKind, InteractionResponseStatus
from semantic_control_kernel.types.interaction import (
    RECOVERY_DIALOG_MAPPINGS,
    USER_INTERACTION_MAPPINGS,
    response_value_field,
    validate_user_interaction_request,
    validate_user_interaction_response,
)
from semantic_control_kernel.validation.contract_validation import (
    EnumValidationError,
    KernelContractError,
    MissingRequiredFieldError,
    validate_contract,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"

DRIFT_PREFLIGHT_STATUS = "drift_preflight: build_plan_authority_applied"
DRIFT_PREFLIGHT_DETAILS = (
    "08_user_function_surface.md resolves Kernel-owned dialogs through KernelUserInteractionService and ClientFrontendEventSink.",
    "11_kernel_internal_data_contracts.md records recovery dialog user_visible_cause and recovery_effect inside prefilled_values; Phase 6 requires them.",
)


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name.replace('.', '__')}.valid.json").read_text(encoding="utf-8"))


def test_phase6_drift_preflight_records_build_plan_authority() -> None:
    assert DRIFT_PREFLIGHT_STATUS == "drift_preflight: build_plan_authority_applied"
    assert any("ClientFrontendEventSink" in detail for detail in DRIFT_PREFLIGHT_DETAILS)
    assert any("recovery_effect" in detail for detail in DRIFT_PREFLIGHT_DETAILS)


def test_request_and_response_contracts_keep_required_fields_and_enums() -> None:
    request = _fixture("kernel.user_interaction_request.v1")
    response = _fixture("kernel.user_interaction_response.v1")

    validate_contract(request)
    validate_contract(response)

    request["interaction_kind"] = "__bad_kind__"
    response["response_status"] = "__bad_status__"

    with pytest.raises(EnumValidationError):
        validate_contract(request)
    with pytest.raises(EnumValidationError):
        validate_contract(response)


def test_function_specific_requests_require_exact_response_shape_and_target_identity_fields() -> None:
    request = _fixture("kernel.user_interaction_request.v1")
    request.update(
        {
            "interaction_function": "choose_artifact_root_folder",
            "interaction_kind": InteractionKind.SELECTION.value,
            "dialog_type": DialogType.FOLDER_PICKER.value,
            "response_shape": "path_value",
            "target_identity": {
                "target_hash": "tgt_phase6",
                "artifact_root_path_hash": "art_phase6",
            },
            "expiration_policy": {
                "policy_id": "selection_short",
                "ttl_seconds": 1800,
                "expires_at": "2026-05-06T00:30:00Z",
                "recovery_state": "expired_pending_interaction",
            },
        }
    )

    validate_user_interaction_request(request)

    missing_target_field = deepcopy(request)
    missing_target_field["target_identity"].pop("artifact_root_path_hash")
    with pytest.raises(MissingRequiredFieldError):
        validate_user_interaction_request(missing_target_field)

    wrong_response_shape = deepcopy(request)
    wrong_response_shape["response_shape"] = "choice_id"
    with pytest.raises(KernelContractError):
        validate_user_interaction_request(wrong_response_shape)

    user_confirmation = deepcopy(request)
    user_confirmation.update(
        {
            "interaction_function": "user_confirmation",
            "interaction_kind": InteractionKind.CONFIRMATION.value,
            "dialog_type": DialogType.GENERIC_CONFIRMATION.value,
            "response_shape": "confirmation_decision",
            "target_identity": {},
            "expiration_policy": {
                "policy_id": "confirmation_destructive",
                "ttl_seconds": 900,
                "expires_at": "2026-05-06T00:15:00Z",
                "recovery_state": "expired_pending_interaction",
            },
        }
    )
    with pytest.raises(MissingRequiredFieldError):
        validate_user_interaction_request(user_confirmation)


def test_submitted_response_requires_exactly_one_mutation_value() -> None:
    response = _fixture("kernel.user_interaction_response.v1")
    response["response_status"] = InteractionResponseStatus.SUBMITTED.value

    validate_user_interaction_response(response)

    zero_values = deepcopy(response)
    zero_values.pop(response_value_field(response) or "path_value")
    with pytest.raises(KernelContractError):
        validate_user_interaction_response(zero_values)

    two_values = deepcopy(response)
    two_values["choice_id"] = "unexpected_second_value"
    with pytest.raises(KernelContractError):
        validate_user_interaction_response(two_values)


def test_non_submitted_response_only_carries_cancellation_reason() -> None:
    response = _fixture("kernel.user_interaction_response.v1")
    response["response_status"] = InteractionResponseStatus.CANCELLED.value
    response.pop(response_value_field(response) or "path_value")
    response["cancellation_reason"] = "user_cancelled"

    validate_user_interaction_response(response)

    response["choice_id"] = "unexpected"
    with pytest.raises(KernelContractError):
        validate_user_interaction_response(response)


def test_recovery_dialog_requests_require_phase6_recovery_fields() -> None:
    request = _fixture("kernel.user_interaction_request.v1")
    request.update(
        {
            "dialog_type": DialogType.RECOVERY_DIALOG.value,
            "interaction_function": "kernel_recovery_dialog",
            "interaction_kind": InteractionKind.RECOVERY.value,
            "options": [],
            "prefilled_values": {
                "recovery_effect": "Keeps the workflow blocked until a safe lock decision is made.",
                "user_visible_cause": "A lock may be stale.",
            },
            "recovery_dialog_type": "stale_lock_dialog",
            "recovery_id": "rcv_test",
            "risk_class": "read_only",
        }
    )

    validate_user_interaction_request(request)

    for field in ("recovery_id", "risk_class", "options", "prefilled_values"):
        missing = deepcopy(request)
        missing.pop(field)
        with pytest.raises(MissingRequiredFieldError):
            validate_user_interaction_request(missing)
    for field in ("user_visible_cause", "recovery_effect"):
        missing = deepcopy(request)
        missing["prefilled_values"].pop(field)
        with pytest.raises(MissingRequiredFieldError):
            validate_user_interaction_request(missing)


def test_recovery_dialog_type_catalog_matches_phase6_table() -> None:
    assert set(RECOVERY_DIALOG_MAPPINGS) == {
        "path_reselection_dialog",
        "missing_input_dialog",
        "overwrite_decision_dialog",
        "merge_reconciliation_dialog",
        "stale_lock_dialog",
        "rebind_database_artifact_tree_dialog",
        "discard_or_archive_staged_work_dialog",
        "partial_pipeline_run_recovery_dialog",
        "support_bundle_dialog",
    }
    assert "choose_merge_projection_mode" in USER_INTERACTION_MAPPINGS
    assert len(USER_INTERACTION_MAPPINGS) == 11
