from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.validation.llm.common import ValidationError


def target_schema_errors(value: Any, schema: Mapping[str, Any], path: str = "$") -> list[ValidationError]:
    variants = schema.get("anyOf")
    if isinstance(variants, list) and variants:
        variant_errors = [
            target_schema_errors(value, variant, path)
            for variant in variants
            if isinstance(variant, Mapping)
        ]
        if any(not errors for errors in variant_errors):
            return []
        return variant_errors[0] if variant_errors else []

    schema_type = schema.get("type")
    if not schema_type_matches(value, schema_type):
        expected = ", ".join(str(item) for item in schema_type) if isinstance(schema_type, list) else str(schema_type)
        return [("function_rule_violation", f"{path} must match schema type {expected}.", path)]

    if "enum" in schema and value not in schema["enum"]:
        return [("enum_mismatch", f"{path} must be one of {schema['enum']!r}.", path)]

    if value is None:
        return []

    errors: list[ValidationError] = []
    if isinstance(value, Mapping) and schema_allows_type(schema_type, "object"):
        properties = schema.get("properties", {})
        if isinstance(properties, Mapping):
            required = schema.get("required", ())
            if isinstance(required, list):
                for key in required:
                    if key not in value:
                        errors.append(("missing_required_fields", f"{path}.{key} is required by target schema.", f"{path}.{key}"))
            if schema.get("additionalProperties") is False:
                for key in sorted(set(value) - set(properties)):
                    errors.append(("unknown_fields", f"{path}.{key} is not allowed by target schema.", f"{path}.{key}"))
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, Mapping):
                    errors.extend(target_schema_errors(value[key], child_schema, f"{path}.{key}"))
    elif isinstance(value, list) and schema_allows_type(schema_type, "array"):
        items = schema.get("items")
        if isinstance(items, Mapping):
            for index, item in enumerate(value):
                errors.extend(target_schema_errors(item, items, f"{path}[{index}]"))
    return errors


def schema_type_matches(value: Any, schema_type: Any) -> bool:
    if schema_type is None:
        return True
    if isinstance(schema_type, list):
        return any(schema_type_matches(value, item) for item in schema_type)
    if schema_type == "null":
        return value is None
    if schema_type == "object":
        return isinstance(value, Mapping)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    return True


def schema_allows_type(schema_type: Any, expected: str) -> bool:
    return schema_type == expected or (isinstance(schema_type, list) and expected in schema_type)
