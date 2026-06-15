from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any

from semantic_control_kernel.validation.contract_errors import (
    EnumValidationError,
    MissingRequiredFieldError,
    SchemaVersionMismatchError,
    UnknownFieldError,
)


def require_schema_version(payload: Mapping[str, Any], expected: str) -> None:
    actual = payload.get("schema_version")
    if actual is None:
        raise MissingRequiredFieldError("Missing required field schema_version.")
    if actual != expected:
        raise SchemaVersionMismatchError(f"Expected schema_version {expected}, got {actual!r}.")


def reject_unknown_fields(payload: Mapping[str, Any], allowed_fields: Iterable[str], contract_name: str) -> None:
    allowed = set(allowed_fields)
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise UnknownFieldError(f"{contract_name} has unknown field(s): {', '.join(unknown)}")


def require_required_fields(
    payload: Mapping[str, Any],
    required_fields: Iterable[str],
    contract_name: str,
) -> None:
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise MissingRequiredFieldError(f"{contract_name} missing required field(s): {', '.join(missing)}")


def validate_enum(value: Any, enum_values: Iterable[str] | type[Enum], field_path: str) -> None:
    allowed = enum_values_as_strings(enum_values)
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_enum(item, allowed, f"{field_path}[{index}]")
        return
    if value not in allowed:
        raise EnumValidationError(f"{field_path} must be one of {sorted(allowed)}, got {value!r}.")


def values_at_path(payload: Mapping[str, Any], field_path: str) -> list[Any]:
    parts = field_path.split(".")
    values: list[Any] = [payload]
    for part in parts:
        next_values: list[Any] = []
        if part.endswith("[]"):
            key = part[:-2]
            for value in values:
                if isinstance(value, Mapping) and key in value:
                    child = value[key]
                    if isinstance(child, list):
                        next_values.extend(child)
                    else:
                        next_values.append(child)
        else:
            for value in values:
                if isinstance(value, Mapping) and part in value:
                    next_values.append(value[part])
        values = next_values
    return values


def enum_values_as_strings(enum_values: Iterable[str] | type[Enum]) -> set[str]:
    if isinstance(enum_values, type) and issubclass(enum_values, Enum):
        return {member.value for member in enum_values}
    return {str(value) for value in enum_values}


def matches_kind(value: Any, expected_kind: str) -> bool:
    if expected_kind == "bool":
        return isinstance(value, bool)
    if expected_kind == "list":
        return isinstance(value, list)
    if expected_kind == "mapping":
        return isinstance(value, Mapping)
    if expected_kind == "string":
        return isinstance(value, str)
    raise AssertionError(f"Unsupported field kind rule: {expected_kind}")


def reject_extensions_field(value: Any, contract_name: str, path: str = "") -> None:
    if isinstance(value, Mapping):
        if "extensions" in value:
            dotted = f"{path}.extensions" if path else "extensions"
            raise UnknownFieldError(f"{contract_name} does not allow {dotted}.")
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            reject_extensions_field(child, contract_name, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_extensions_field(child, contract_name, f"{path}[{index}]")
