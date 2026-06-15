from __future__ import annotations

from typing import Any

from ..taxonomy import TaxonomyProfile


def value_type_schema(value_type: str, *, allow_object: bool = False) -> dict[str, Any]:
    mapping = {
        "string": ["string", "null"],
        "number": ["number", "null"],
        "boolean": ["boolean", "null"],
        "date_or_string": ["string", "null"],
        "number_or_string": ["number", "string", "null"],
        "number_or_money_string": ["number", "string", "null"],
    }
    types = mapping.get(value_type, ["string", "number", "boolean", "null"])
    return {"type": types}


def field_value_schema(value_type: str, *, cardinality: str, allow_object: bool = False) -> dict[str, Any]:
    if cardinality != "multi":
        return value_type_schema(value_type, allow_object=allow_object)
    item_schema = without_null_type(value_type_schema(value_type, allow_object=allow_object))
    return {"type": ["array", "null"], "items": item_schema}


def without_null_type(schema: dict[str, Any]) -> dict[str, Any]:
    result = dict(schema)
    schema_type = result.get("type")
    if isinstance(schema_type, list):
        result["type"] = [item for item in schema_type if item != "null"] or ["string"]
    elif schema_type == "null":
        result["type"] = "string"
    return result


def promotion_field_specs(profile: TaxonomyProfile) -> dict[str, dict[str, str]]:
    slot_defs = {
        str(slot_def.get("slot") or "").strip(): slot_def
        for slot_def in profile.promotion_slots
        if isinstance(slot_def, dict) and str(slot_def.get("slot") or "").strip()
    }
    specs: dict[str, dict[str, str]] = {}
    for rule in profile.promotion_rules:
        if not isinstance(rule, dict):
            continue
        slot = str(rule.get("slot") or "").strip()
        slot_def = slot_defs.get(slot, {})
        cardinality = str(slot_def.get("cardinality") or "single")
        value_type = str(slot_def.get("value_type") or "string")
        for source_path in rule.get("source_paths", []) or []:
            field_code = field_code_from_source_path(str(source_path or ""))
            if field_code and (field_code not in specs or specs[field_code]["cardinality"] != "multi"):
                specs[field_code] = {"cardinality": cardinality, "value_type": value_type}
    return specs


def field_code_from_source_path(source_path: str) -> str | None:
    prefix = "content.fields."
    if not source_path.startswith(prefix):
        return None
    tail = source_path[len(prefix) :]
    field_code = tail.split(".", 1)[0].split("[", 1)[0].strip()
    return field_code or None
