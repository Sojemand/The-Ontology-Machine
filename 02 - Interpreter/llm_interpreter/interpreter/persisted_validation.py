"""Persisted-output validation against the visible schema contract."""
from __future__ import annotations

from typing import Any

from ..prompts import get_persisted_output_schema
from ..providers import ProviderError


def validate_persisted_output_shape(payload: dict[str, Any]) -> None:
    _validate_schema_value(payload, get_persisted_output_schema(), "persisted_output")


def _validate_schema_value(value: Any, schema: dict[str, Any], label: str) -> None:
    expected_types = _normalize_types(schema.get("type"))
    if expected_types and not any(_matches_type(value, expected_type) for expected_type in expected_types):
        raise ProviderError(f"Persisted Output ungueltig: {label} muss {_describe_types(expected_types)} sein")
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        raise ProviderError(f"Persisted Output ungueltig: {label} hat einen unerlaubten Wert")
    if isinstance(value, dict):
        _validate_object(value, schema, label)
    elif isinstance(value, list):
        _validate_array(value, schema, label)


def _validate_object(value: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, dict):
        properties = {}
    if not isinstance(required, list):
        required = []
    for key in required:
        if key not in value:
            raise ProviderError(f"Persisted Output ungueltig: {label}.{key} fehlt")
    if schema.get("additionalProperties") is False:
        unknown_keys = [key for key in value if key not in properties]
        if unknown_keys:
            raise ProviderError(f"Persisted Output ungueltig: {label} enthaelt unerlaubte Felder")
    for key, child_schema in properties.items():
        if key in value and isinstance(child_schema, dict):
            _validate_schema_value(value[key], child_schema, f"{label}.{key}")


def _validate_array(value: list[Any], schema: dict[str, Any], label: str) -> None:
    item_schema = schema.get("items")
    if not isinstance(item_schema, dict):
        return
    for index, item in enumerate(value):
        _validate_schema_value(item, item_schema, f"{label}[{index}]")


def _normalize_types(schema_type: Any) -> tuple[str, ...]:
    if isinstance(schema_type, str):
        return (schema_type,)
    if isinstance(schema_type, list):
        return tuple(item for item in schema_type if isinstance(item, str))
    return ()


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True


def _describe_types(expected_types: tuple[str, ...]) -> str:
    return " oder ".join(expected_types)


__all__ = ["validate_persisted_output_shape"]
