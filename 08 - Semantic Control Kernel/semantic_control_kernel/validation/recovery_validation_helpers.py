from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.validation.contract_validation import (
    EnumValidationError,
    KernelContractError,
    MissingRequiredFieldError,
    UnknownFieldError,
)
from semantic_control_kernel.validation.recovery_validation_schema import FORBIDDEN_AGENT_AUTHORED_FIELDS


def validate_closed_payload(
    payload: Mapping[str, Any],
    schema_version: str,
    fields: tuple[str, ...],
    *,
    allow_any_schema: bool = False,
) -> None:
    if not isinstance(payload, Mapping):
        raise KernelContractError(f"{schema_version or 'contract'} must be an object.")
    missing = [field for field in fields if field not in payload]
    if missing:
        raise MissingRequiredFieldError(f"{schema_version or 'contract'} missing required field(s): {', '.join(missing)}")
    unknown = sorted(set(payload) - set(fields))
    if unknown:
        raise UnknownFieldError(f"{schema_version or 'contract'} has unknown field(s): {', '.join(unknown)}")
    if not allow_any_schema and payload.get("schema_version") != schema_version:
        raise KernelContractError(f"Expected schema_version {schema_version}, got {payload.get('schema_version')!r}.")
    if allow_any_schema and not isinstance(payload.get("schema_version"), str):
        raise MissingRequiredFieldError("Missing required field schema_version.")


def validate_enum(value: Any, enum_values: Any, field_path: str) -> None:
    if isinstance(enum_values, type):
        allowed = {member.value for member in enum_values}
    else:
        allowed = {str(item) for item in enum_values}
    if value not in allowed:
        raise EnumValidationError(f"{field_path} must be one of {sorted(allowed)}, got {value!r}.")


def validate_allowed_tools(values: Any, field_path: str) -> None:
    if not isinstance(values, list):
        raise KernelContractError(f"{field_path} must be a list.")
    for tool in values:
        if not isinstance(tool, str):
            raise KernelContractError(f"{field_path} items must be strings.")


def reject_agent_authored_domain_payloads(value: Any, path: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in FORBIDDEN_AGENT_AUTHORED_FIELDS:
                raise UnknownFieldError(f"{path} forbids Agent-authored domain field {key}.")
            reject_agent_authored_domain_payloads(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_agent_authored_domain_payloads(child, f"{path}[{index}]")
