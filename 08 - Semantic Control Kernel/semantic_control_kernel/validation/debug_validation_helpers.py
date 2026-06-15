from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from semantic_control_kernel.validation.contract_validation import KernelContractError, MissingRequiredFieldError, UnknownFieldError


def validate_closed_payload(
    payload: Mapping[str, Any],
    schema_version: str,
    required_fields: tuple[str, ...],
    optional_fields: tuple[str, ...] = (),
) -> None:
    if not isinstance(payload, Mapping):
        raise KernelContractError(f"{schema_version} must be an object.")
    missing = [field_name for field_name in required_fields if field_name not in payload]
    if missing:
        raise MissingRequiredFieldError(f"{schema_version} missing required field(s): {', '.join(missing)}")
    unknown = sorted(set(payload) - set(required_fields) - set(optional_fields))
    if unknown:
        raise UnknownFieldError(f"{schema_version} has unknown field(s): {', '.join(unknown)}")
    if payload.get("schema_version") != schema_version:
        raise KernelContractError(f"Expected schema_version {schema_version}, got {payload.get('schema_version')!r}.")


def ensure_mapping(value: Any, field_path: str) -> None:
    if not isinstance(value, Mapping):
        raise KernelContractError(f"{field_path} must be an object.")


def ensure_sequence(value: Any, field_path: str, *, allow_none: bool = False) -> None:
    if allow_none and value is None:
        return
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise KernelContractError(f"{field_path} must be a list.")


def ensure_sequence_of_mappings_or_strings(value: Any, field_path: str, *, allow_none: bool = False) -> None:
    ensure_sequence(value, field_path, allow_none=allow_none)
    if value is None:
        return
    for item in value:
        if not isinstance(item, (Mapping, str)):
            raise KernelContractError(f"{field_path} items must be objects or strings.")


def ensure_enum(value: Any, allowed: tuple[str, ...], field_path: str) -> None:
    if value not in allowed:
        raise KernelContractError(f"{field_path} must be one of {sorted(allowed)}, got {value!r}.")
