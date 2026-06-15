from __future__ import annotations

from typing import Any

from .tool_handler_types import ToolFailure


def validate_arguments(tool_name: str, arguments: dict[str, Any], schema: dict[str, Any] | None) -> None:
    if not schema:
        return
    if not isinstance(arguments, dict):
        raise ToolFailure(f"{tool_name} erwartet ein Argument-Objekt.")
    _validate_object(tool_name, arguments, schema, tool_name, required_message="{key} fehlt oder ist ungueltig.")


def _validate_object(
    tool_name: str,
    value: dict[str, Any],
    schema: dict[str, Any],
    path: str,
    *,
    required_message: str = "{key} fehlt.",
) -> None:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    if schema.get("additionalProperties") is False:
        unknown = sorted(set(value) - set(properties))
        if unknown:
            if not properties:
                raise ToolFailure(f"{tool_name} akzeptiert keine Argumente.")
            raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")
    for key in schema.get("required") or []:
        if key not in value or value[key] is None:
            raise ToolFailure(required_message.format(key=_field_path(path, key)))
    for key, item in value.items():
        child_schema = properties.get(key)
        if isinstance(child_schema, dict):
            _validate_value(item, child_schema, _field_path(path, key), key)


def _validate_value(value: Any, schema: dict[str, Any], path: str, key: str) -> None:
    if value is None or value == "":
        return
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            raise ToolFailure(f"{path} muss ein Objekt sein.")
        _validate_object(path, value, schema, path)
    elif expected_type == "array":
        if not isinstance(value, list):
            _raise_array_type(path, schema)
        _validate_array_items(value, schema, path)
    elif expected_type == "string":
        if not isinstance(value, str):
            raise ToolFailure(f"{path} muss ein String sein.")
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            raise ToolFailure(f"{path} muss ein Bool sein.")
    elif expected_type == "integer":
        _validate_integer(value, schema, path)
    elif expected_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ToolFailure(f"{path} muss eine Zahl sein.")
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        raise ToolFailure(f"{path} muss eines von {', '.join(map(str, enum_values))} sein.")


def _validate_integer(value: Any, schema: dict[str, Any], path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        _raise_integer_range(path, schema)
    minimum = schema.get("minimum")
    if isinstance(minimum, (int, float)) and value < minimum:
        _raise_integer_range(path, schema)
    maximum = schema.get("maximum")
    if isinstance(maximum, (int, float)) and value > maximum:
        raise ToolFailure(f"{path} muss hoechstens {int(maximum)} sein.")


def _validate_array_items(value: list[Any], schema: dict[str, Any], path: str) -> None:
    item_schema = schema.get("items")
    if not isinstance(item_schema, dict) or not item_schema:
        return
    if item_schema.get("type") == "string" and any(not isinstance(item, str) for item in value):
        raise ToolFailure(f"{path} muss eine String-Liste sein.")
    for index, item in enumerate(value):
        _validate_value(item, item_schema, f"{path}[{index}]", path)


def _raise_array_type(path: str, schema: dict[str, Any]) -> None:
    items = schema.get("items")
    if isinstance(items, dict) and items.get("type") == "string":
        raise ToolFailure(f"{path} muss eine String-Liste sein.")
    raise ToolFailure(f"{path} muss eine Liste sein.")


def _raise_integer_range(path: str, schema: dict[str, Any]) -> None:
    minimum = schema.get("minimum")
    if minimum == 0:
        raise ToolFailure(f"{path} muss eine nicht-negative Ganzzahl sein.")
    if isinstance(minimum, (int, float)) and minimum >= 1:
        raise ToolFailure(f"{path} muss eine positive Ganzzahl sein.")
    raise ToolFailure(f"{path} muss eine Ganzzahl sein.")


def _field_path(parent: str, key: str) -> str:
    return key if "." in parent or parent == key else key


__all__ = ["validate_arguments"]
