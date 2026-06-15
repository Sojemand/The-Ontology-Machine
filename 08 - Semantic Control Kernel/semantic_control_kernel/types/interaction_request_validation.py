from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.enums import DialogType, InteractionKind
from semantic_control_kernel.types.events import UserInteractionRequest
from semantic_control_kernel.types.interaction_mappings import RECOVERY_DIALOG_MAPPINGS, USER_INTERACTION_MAPPINGS
from semantic_control_kernel.types.interaction_response_validation import _policy_id
from semantic_control_kernel.validation.contract_validation import (
    KernelContractError,
    MissingRequiredFieldError,
    validate_contract,
)


def validate_user_interaction_request(request: UserInteractionRequest | Mapping[str, Any]) -> None:
    payload = request.to_dict() if isinstance(request, UserInteractionRequest) else dict(request)
    validate_contract(payload, expected_schema_version=UserInteractionRequest.SCHEMA_VERSION)
    interaction_function = payload["interaction_function"]
    mapping = USER_INTERACTION_MAPPINGS.get(interaction_function)
    if mapping is not None:
        _validate_mapped_request(payload, interaction_function, mapping)
    elif payload["interaction_kind"] != InteractionKind.RECOVERY.value:
        raise KernelContractError(f"Unknown Kernel interaction function: {interaction_function}")
    if payload["dialog_type"] == DialogType.RECOVERY_DIALOG.value:
        _validate_recovery_dialog_request(payload)


def _validate_mapped_request(payload: dict[str, Any], interaction_function: str, mapping) -> None:
    if payload["interaction_kind"] != mapping.interaction_kind:
        raise KernelContractError(f"{interaction_function} must use interaction_kind {mapping.interaction_kind}.")
    if payload["dialog_type"] != mapping.dialog_type:
        raise KernelContractError(f"{interaction_function} must use dialog_type {mapping.dialog_type}.")
    policy_id = _policy_id(payload["expiration_policy"])
    if policy_id != mapping.expiration_policy_id:
        raise KernelContractError(f"{interaction_function} must use expiration policy {mapping.expiration_policy_id}.")
    if payload["response_shape"] != mapping.response_shape:
        raise KernelContractError(f"{interaction_function} must use response_shape {mapping.response_shape}.")
    target_identity = payload["target_identity"]
    if interaction_function == "user_confirmation" and not target_identity:
        raise MissingRequiredFieldError("user_confirmation requires the active Phase 5 target_identity.")
    missing = [field_name for field_name in mapping.required_target_identity_fields if field_name not in target_identity]
    if missing:
        raise MissingRequiredFieldError(
            f"{interaction_function} target_identity missing required field(s): {', '.join(missing)}."
        )


def _validate_recovery_dialog_request(payload: dict[str, Any]) -> None:
    recovery_type = payload.get("recovery_dialog_type")
    if recovery_type not in RECOVERY_DIALOG_MAPPINGS:
        raise KernelContractError(f"Unknown recovery dialog type: {recovery_type!r}")
    for field_name in ("recovery_id", "risk_class", "options"):
        if field_name not in payload:
            raise MissingRequiredFieldError(
                f"kernel.user_interaction_request.v1 recovery dialogs require {field_name}."
            )
    metadata = payload.get("prefilled_values")
    if not isinstance(metadata, Mapping):
        raise MissingRequiredFieldError(
            "kernel.user_interaction_request.v1 recovery dialogs require prefilled_values metadata."
        )
    for field_name in ("user_visible_cause", "recovery_effect"):
        if field_name not in metadata:
            raise MissingRequiredFieldError(
                f"kernel.user_interaction_request.v1 recovery dialogs require {field_name}."
            )
