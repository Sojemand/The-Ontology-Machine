from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

TAXONOMY_CODE_SECTIONS = (
    "domains",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
)


def taxonomy_allowed_codes(taxonomy_ref: Mapping[str, Any]) -> set[str]:
    codes = {str(item) for item in _sequence(taxonomy_ref.get("codes")) if str(item)}
    explicit = taxonomy_ref.get("allowed_codes")
    if isinstance(explicit, Mapping):
        for value in explicit.values():
            codes.update(str(item) for item in _sequence(value) if str(item))
    else:
        codes.update(str(item) for item in _sequence(explicit) if str(item))
    codes.update(code for values in taxonomy_section_codes(taxonomy_ref).values() for code in values)
    return codes or {"other"}


def taxonomy_fallback_codes(taxonomy_ref: Mapping[str, Any], allowed_codes: set[str]) -> set[str]:
    values: list[Any] = []
    explicit = taxonomy_ref.get("fallback_codes")
    if isinstance(explicit, Mapping):
        values.extend(explicit.values())
    else:
        values.extend(_sequence(explicit))
    defaults = taxonomy_ref.get("defaults")
    if isinstance(defaults, Mapping):
        values.extend(defaults.values())
    codes = {str(item) for item in values if str(item)}
    codes = {code for code in codes if not allowed_codes or code in allowed_codes}
    return codes or ({"other"} if "other" in allowed_codes else set())


def taxonomy_term_summaries(taxonomy_ref: Mapping[str, Any], allowed_codes: set[str]) -> dict[str, str]:
    summaries: dict[str, list[str]] = {}
    for section in TAXONOMY_CODE_SECTIONS:
        for item in taxonomy_sequence(taxonomy_ref.get(section)):
            code = taxonomy_code(item)
            if code and code in allowed_codes:
                summaries.setdefault(code, []).append(taxonomy_term_summary(section, item, code))
    explicit = taxonomy_ref.get("term_summaries")
    if isinstance(explicit, Mapping):
        for key, value in explicit.items():
            code = str(key)
            if code in allowed_codes:
                summaries.setdefault(code, []).append(str(value))
    return {
        code: " | ".join(dict.fromkeys(summaries.get(code, [code.replace("_", " ")])))
        for code in sorted(allowed_codes)
    }


def taxonomy_allowed_codes_by_section(taxonomy_ref: Mapping[str, Any]) -> dict[str, list[str]]:
    explicit = taxonomy_ref.get("allowed_codes")
    if isinstance(explicit, Mapping):
        return {
            str(key): sorted(str(item) for item in value if str(item))
            for key, value in explicit.items()
            if _sequence(value)
        }
    sectioned = taxonomy_section_codes(taxonomy_ref)
    return sectioned or {"codes": sorted(taxonomy_allowed_codes(taxonomy_ref))}


def taxonomy_fallback_codes_view(taxonomy_ref: Mapping[str, Any], fallback_codes: set[str]) -> dict[str, str]:
    explicit = taxonomy_ref.get("fallback_codes")
    if isinstance(explicit, Mapping):
        return {str(key): str(value) for key, value in explicit.items() if str(value)}
    defaults = taxonomy_ref.get("defaults")
    if isinstance(defaults, Mapping):
        return {
            str(key).replace("fallback_", ""): str(value)
            for key, value in defaults.items()
            if str(value)
        }
    return {"default": sorted(fallback_codes)[0]} if fallback_codes else {}


def taxonomy_promotion_slots(taxonomy_ref: Mapping[str, Any]) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in taxonomy_sequence(taxonomy_ref.get("promotion_slots")):
        if isinstance(item, Mapping):
            value = str(item.get("slot") or "")
            definition = deepcopy(dict(item))
        else:
            value = str(item)
            definition = {
                "slot": value,
                "label": value.replace("_", " ").title(),
                "description": None,
                "value_type": "string",
                "scope": "document",
                "cardinality": "single",
                "query_role": None,
                "display_rank": None,
            }
        if value and value not in seen:
            definition.setdefault("label", value.replace("_", " ").title())
            definition.setdefault("description", None)
            definition.setdefault("value_type", "string")
            definition.setdefault("scope", "document")
            definition.setdefault("cardinality", "single")
            definition.setdefault("query_role", None)
            definition.setdefault("display_rank", None)
            slots.append(definition)
            seen.add(value)
    return slots


def taxonomy_sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def taxonomy_section_codes(taxonomy_ref: Mapping[str, Any]) -> dict[str, list[str]]:
    sectioned: dict[str, list[str]] = {}
    for section in TAXONOMY_CODE_SECTIONS:
        codes = sorted(code for code in (taxonomy_code(item) for item in taxonomy_sequence(taxonomy_ref.get(section))) if code)
        if codes:
            sectioned[section] = codes
    return sectioned


def taxonomy_code(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("code") or item.get("id") or "")
    if isinstance(item, str):
        return item
    return ""


def taxonomy_term_summary(section: str, item: Any, code: str) -> str:
    if not isinstance(item, Mapping):
        return code.replace("_", " ")
    parts = [f"section={section}"]
    for key in ("label", "description", "value_type"):
        if item.get(key):
            parts.append(f"{key}={item[key]}")
    for key in ("domains", "allowed_categories", "allowed_subcategories"):
        value = item.get(key)
        if isinstance(value, list) and value:
            parts.append(f"{key}={', '.join(str(child) for child in value)}")
    return "; ".join(parts)


def _sequence(value: Any) -> Sequence[Any]:
    return taxonomy_sequence(value)
