from __future__ import annotations

from typing import Any, Mapping, Sequence


JsonSchema = dict[str, Any]


def schema_supports_strict(schema: Mapping[str, Any] | None) -> bool:
    if not isinstance(schema, Mapping):
        return False
    schema_type = schema.get("type")
    if _has_type(schema_type, "object"):
        if schema.get("additionalProperties") is not False:
            return False
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            return False
        required = schema.get("required")
        if not isinstance(required, list) or set(required) != set(properties.keys()):
            return False
        for subschema in properties.values():
            if isinstance(subschema, Mapping) and not schema_supports_strict(subschema):
                return False
    if _has_type(schema_type, "array"):
        items = schema.get("items")
        if isinstance(items, Mapping) and not schema_supports_strict(items):
            return False
    variants = schema.get("anyOf")
    if isinstance(variants, list):
        for variant in variants:
            if isinstance(variant, Mapping) and not schema_supports_strict(variant):
                return False
    return True


def _has_type(schema_type: Any, expected: str) -> bool:
    return schema_type == expected or (isinstance(schema_type, list) and expected in schema_type)


def _object(properties: Mapping[str, JsonSchema]) -> JsonSchema:
    copied = dict(properties)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(copied.keys()),
        "properties": copied,
    }


def _nullable_object(properties: Mapping[str, JsonSchema]) -> JsonSchema:
    schema = _object(properties)
    schema["type"] = ["object", "null"]
    return schema


def _array(items: JsonSchema) -> JsonSchema:
    return {"type": "array", "items": items}


def _nullable_array(items: JsonSchema) -> JsonSchema:
    return {"type": ["array", "null"], "items": items}


def _string() -> JsonSchema:
    return {"type": "string"}


def _nullable_string() -> JsonSchema:
    return {"type": ["string", "null"]}


def _number() -> JsonSchema:
    return {"type": "number"}


def _nullable_number() -> JsonSchema:
    return {"type": ["number", "null"]}


def _integer() -> JsonSchema:
    return {"type": "integer"}


def _nullable_integer() -> JsonSchema:
    return {"type": ["integer", "null"]}


def _boolean() -> JsonSchema:
    return {"type": "boolean"}


def _string_array() -> JsonSchema:
    return _array(_string())


def _nullable_string_array() -> JsonSchema:
    return _nullable_array(_string())


def _const(value: str) -> JsonSchema:
    return {"type": "string", "enum": [value]}


def _enum(values: Sequence[str], *, fallback: Sequence[str] = ()) -> JsonSchema:
    normalized = [str(value) for value in values if str(value)]
    normalized.extend(str(value) for value in fallback if str(value))
    unique = list(dict.fromkeys(normalized))
    if not unique:
        return _string()
    return {"type": "string", "enum": unique}


def _nullable_enum(values: Sequence[str], *, fallback: Sequence[str] = ()) -> JsonSchema:
    schema = _enum(values, fallback=fallback)
    if "enum" not in schema:
        return _nullable_string()
    return {"type": ["string", "null"], "enum": [*schema["enum"], None]}
