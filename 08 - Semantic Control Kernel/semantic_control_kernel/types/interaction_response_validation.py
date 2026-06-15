from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.enums import InteractionKind, InteractionResponseStatus, RecoveryDialogType
from semantic_control_kernel.types.events import UserInteractionRequest, UserInteractionResponse
from semantic_control_kernel.types.interaction_mappings import (
    CANCELLATION_REASON_VALUES,
    RECOVERY_DIALOG_MAPPINGS,
    RESPONSE_VALUE_FIELDS,
    USER_INTERACTION_MAPPINGS,
)
from semantic_control_kernel.validation.contract_validation import (
    KernelContractError,
    MissingRequiredFieldError,
    UnknownFieldError,
    validate_contract,
)


def validate_user_interaction_response(response: UserInteractionResponse | Mapping[str, Any]) -> None:
    payload = response.to_dict() if isinstance(response, UserInteractionResponse) else dict(response)
    validate_contract(payload, expected_schema_version=UserInteractionResponse.SCHEMA_VERSION)
    populated_values = [field for field in RESPONSE_VALUE_FIELDS if field in payload and payload[field] not in (None, "", [])]
    response_status = payload["response_status"]
    if response_status == InteractionResponseStatus.SUBMITTED.value:
        value_count = _submitted_value_count(populated_values)
        if value_count != 1:
            raise KernelContractError("Submitted interaction responses must populate exactly one response value field.")
        if "cancellation_reason" in payload:
            raise UnknownFieldError("Submitted interaction responses must not include cancellation_reason.")
        return
    if populated_values:
        raise KernelContractError("Non-submitted interaction responses must not populate response value fields.")
    if payload.get("cancellation_reason") not in CANCELLATION_REASON_VALUES:
        raise MissingRequiredFieldError("Terminal interaction responses must include a valid cancellation_reason.")


def validate_user_interaction_response_for_request(
    request: UserInteractionRequest | Mapping[str, Any],
    response: UserInteractionResponse | Mapping[str, Any],
) -> None:
    request_payload = request.to_dict() if isinstance(request, UserInteractionRequest) else dict(request)
    response_payload = response.to_dict() if isinstance(response, UserInteractionResponse) else dict(response)
    if response_payload["response_status"] != InteractionResponseStatus.SUBMITTED.value:
        return
    if request_payload["interaction_kind"] == InteractionKind.RECOVERY.value:
        _validate_recovery_response_for_request(request_payload, response_payload)
        return
    mapping = USER_INTERACTION_MAPPINGS.get(request_payload["interaction_function"])
    if mapping is None:
        return
    if response_payload.get("recovery_id") not in (None, ""):
        raise UnknownFieldError(f"{request_payload['interaction_function']} responses must not include recovery_id.")
    actual_fields = _submitted_non_recovery_value_fields(response_payload)
    if len(actual_fields) != 1 or actual_fields[0] not in mapping.response_value_fields:
        allowed = ", ".join(mapping.response_value_fields)
        raise KernelContractError(
            f"{request_payload['interaction_function']} submitted responses must populate exactly one of: {allowed}."
        )


def response_value_field(payload: Mapping[str, Any]) -> str | None:
    populated = [field for field in RESPONSE_VALUE_FIELDS if field in payload and payload[field] not in (None, "", [])]
    return populated[0] if len(populated) == 1 else None


def _validate_recovery_response_for_request(
    request_payload: Mapping[str, Any],
    response_payload: Mapping[str, Any],
) -> None:
    expected_recovery_id = request_payload.get("recovery_id")
    if response_payload.get("recovery_id") != expected_recovery_id:
        raise MissingRequiredFieldError("Recovery dialog responses must preserve the request recovery_id.")
    recovery_type = str(request_payload.get("recovery_dialog_type") or "")
    mapping = RECOVERY_DIALOG_MAPPINGS.get(recovery_type)
    if mapping is None:
        raise KernelContractError(f"Unknown recovery dialog type: {recovery_type!r}")
    actual_fields = _submitted_non_recovery_value_fields(response_payload)
    if recovery_type == RecoveryDialogType.PARTIAL_PIPELINE_RUN_RECOVERY_DIALOG.value:
        if actual_fields:
            raise KernelContractError("partial_pipeline_run_recovery_dialog responses must use recovery_id as the selected option.")
        return
    if recovery_type == RecoveryDialogType.SUPPORT_BUNDLE_DIALOG.value:
        if len(actual_fields) > 1 or (actual_fields and actual_fields[0] != "confirmation_decision"):
            raise KernelContractError("support_bundle_dialog responses may omit a mutation value or include only confirmation_decision.")
        return
    if len(actual_fields) != 1 or actual_fields[0] not in mapping.response_value_fields:
        allowed = ", ".join(mapping.response_value_fields)
        raise KernelContractError(
            f"{recovery_type} submitted responses must populate exactly one mapped value field: {allowed}."
        )


def _submitted_value_count(populated_values: list[str]) -> int:
    non_recovery_values = [field for field in populated_values if field != "recovery_id"]
    return len(non_recovery_values) if non_recovery_values else len(populated_values)


def _submitted_non_recovery_value_fields(payload: Mapping[str, Any]) -> list[str]:
    return [
        field
        for field in RESPONSE_VALUE_FIELDS
        if field != "recovery_id" and field in payload and payload[field] not in (None, "", [])
    ]


def _policy_id(expiration_policy: object) -> str | None:
    if isinstance(expiration_policy, Mapping):
        value = expiration_policy.get("policy_id")
        return str(value) if value is not None else None
    return None
