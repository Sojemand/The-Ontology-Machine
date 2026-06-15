from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from semantic_control_kernel.validation.contract_errors import (
    KernelContractError,
    MissingRequiredFieldError,
    UnknownFieldError,
)
from semantic_control_kernel.validation.contract_primitives import (
    reject_unknown_fields,
    require_required_fields,
    values_at_path,
)
from semantic_control_kernel.validation.contract_rules import (
    CLIENT_FRONTEND_EVENT_NESTED_CONTRACTS,
    PIPELINE_BATCH_NESTED_SHAPES,
)


ValidateContractFn = Callable[[Mapping[str, Any], str | None], None]


def validate_schema_specific_rules(
    payload: Mapping[str, Any],
    schema_version: str,
    validate_contract_fn: ValidateContractFn,
) -> None:
    if schema_version == "kernel.user_interaction_request.v1":
        _validate_recovery_dialog_type_rule(payload)
    if schema_version == "kernel.pipeline_batch_manifest.v1":
        _validate_pipeline_batch_manifest(payload)
    if schema_version == "kernel.client_frontend_event.v1":
        _validate_client_frontend_event_contract(payload, validate_contract_fn)
    if schema_version == "kernel.client_frontend_event_batch.v1":
        _validate_client_frontend_event_batch_contract(payload, validate_contract_fn)


def _validate_recovery_dialog_type_rule(payload: Mapping[str, Any]) -> None:
    dialog_type = payload.get("dialog_type")
    has_recovery_dialog_type = "recovery_dialog_type" in payload
    if dialog_type == "recovery_dialog" and not has_recovery_dialog_type:
        raise MissingRequiredFieldError(
            "kernel.user_interaction_request.v1 requires recovery_dialog_type for recovery_dialog."
        )
    if dialog_type != "recovery_dialog" and has_recovery_dialog_type:
        raise UnknownFieldError(
            "kernel.user_interaction_request.v1 forbids recovery_dialog_type for non-recovery dialogs."
        )


def _validate_pipeline_batch_manifest(payload: Mapping[str, Any]) -> None:
    for path, (required, optional) in PIPELINE_BATCH_NESTED_SHAPES.items():
        values = values_at_path(payload, path)
        if not values:
            continue
        for value in values:
            if not isinstance(value, Mapping):
                raise KernelContractError(f"kernel.pipeline_batch_manifest.v1.{path} must be an object.")
            require_required_fields(value, required, f"kernel.pipeline_batch_manifest.v1.{path}")
            reject_unknown_fields(value, set(required) | set(optional), f"kernel.pipeline_batch_manifest.v1.{path}")


def _validate_client_frontend_event_contract(
    payload: Mapping[str, Any],
    validate_contract_fn: ValidateContractFn,
) -> None:
    field_name_by_kind = {
        "interaction_request": "interaction_request",
        "progress_event": "progress_event",
        "mirror_event": "mirror_event",
        "tool_availability": "tool_availability",
        "interaction_resolved": None,
    }
    kind = payload.get("frontend_event_kind")
    if kind not in field_name_by_kind:
        return
    field_name = field_name_by_kind[kind]
    if field_name is None:
        return
    if field_name not in payload:
        raise MissingRequiredFieldError(
            f"kernel.client_frontend_event.v1 requires {field_name} when frontend_event_kind is {kind!r}."
        )
    nested = payload[field_name]
    if not isinstance(nested, Mapping):
        raise KernelContractError(f"kernel.client_frontend_event.v1.{field_name} must be an object.")
    expected_schema = CLIENT_FRONTEND_EVENT_NESTED_CONTRACTS.get(field_name)
    if expected_schema is not None:
        validate_contract_fn(nested, expected_schema)


def _validate_client_frontend_event_batch_contract(
    payload: Mapping[str, Any],
    validate_contract_fn: ValidateContractFn,
) -> None:
    events = payload.get("events")
    if not isinstance(events, list):
        raise KernelContractError("kernel.client_frontend_event_batch.v1.events must be a list.")
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise KernelContractError(
                f"kernel.client_frontend_event_batch.v1.events[{index}] must be an object."
            )
        validate_contract_fn(event, "kernel.client_frontend_event.v1")


__all__ = ["validate_schema_specific_rules"]
