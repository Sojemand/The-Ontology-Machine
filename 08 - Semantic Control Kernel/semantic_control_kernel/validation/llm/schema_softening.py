"""Schema-bounded soft canonicalization for tolerant LLM outputs."""

from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.validation.llm.common import _STATUS_ALIASES
from semantic_control_kernel.validation.llm.schema import schema_allows_type, schema_type_matches


def soften_to_schema(value: Any, schema: Mapping[str, Any], *, key: str = "") -> Any:
    schema_type = schema.get("type")
    if "enum" in schema:
        enum_values = list(schema.get("enum") or [])
        if value in enum_values:
            return value
        if key in {"status", "target_status"} and isinstance(value, str):
            candidate = _STATUS_ALIASES.get(value.strip().lower())
            if candidate in enum_values:
                return candidate
        if value is None and None in enum_values:
            return None
        return value
    if schema_allows_type(schema_type, "object"):
        if not isinstance(value, Mapping):
            return default_for_schema(schema, key=key)
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            return dict(value)
        return {
            str(child_key): soften_to_schema(value[child_key], child_schema, key=str(child_key))
            if child_key in value
            else default_for_schema(child_schema, key=str(child_key))
            for child_key, child_schema in properties.items()
            if isinstance(child_schema, Mapping)
        }
    if schema_allows_type(schema_type, "array"):
        if not isinstance(value, list):
            return []
        items = schema.get("items")
        if not isinstance(items, Mapping):
            return list(value)
        return [soften_to_schema(item, items, key=key) for item in value]
    if not schema_type_matches(value, schema_type):
        if schema_allows_type(schema_type, "string") and value is not None:
            return str(value)
        if schema_allows_type(schema_type, "number"):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default_for_schema(schema, key=key)
        if schema_allows_type(schema_type, "integer"):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default_for_schema(schema, key=key)
        if schema_allows_type(schema_type, "boolean"):
            return bool(value)
        if schema_allows_type(schema_type, "null"):
            return None
    return value


def default_for_schema(schema: Mapping[str, Any], *, key: str = "") -> Any:
    schema_type = schema.get("type")
    enum_values = [item for item in schema.get("enum", ()) if item is not None]
    if key in {"status", "target_status"} and "draft" in enum_values:
        return "draft"
    if len(enum_values) == 1:
        return enum_values[0]
    if schema_allows_type(schema_type, "null"):
        return None
    if schema_allows_type(schema_type, "array"):
        return []
    if schema_allows_type(schema_type, "object"):
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            return {}
        return {
            str(child_key): default_for_schema(child_schema, key=str(child_key))
            for child_key, child_schema in properties.items()
            if isinstance(child_schema, Mapping)
        }
    if schema_allows_type(schema_type, "string"):
        return ""
    if schema_allows_type(schema_type, "integer"):
        return 0
    if schema_allows_type(schema_type, "number"):
        return 0.0
    if schema_allows_type(schema_type, "boolean"):
        return False
    return None


__all__ = ["default_for_schema", "soften_to_schema"]
