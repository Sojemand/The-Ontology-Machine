"""Value parsers for projection draft creation."""
from __future__ import annotations

import re
from typing import Any

from ..taxonomy_sources import policy as source_policy

LIST_SPLIT_RE = re.compile(r"[\n,;]+")
PROJECTION_ID_RE = re.compile(r"^[a-z0-9]+(?:[._][a-z0-9]+)*$")
TOP_LEVEL_COVERAGE_FIELDS = (
    "domain_ids",
    "include_document_types",
    "include_categories",
    "include_subcategories",
    "include_field_codes",
    "include_row_types",
    "include_cell_codes",
)


def first_present(payload: dict[str, Any], nested_payload: dict[str, Any], field_name: str) -> Any:
    if field_name in payload:
        return payload.get(field_name)
    return nested_payload.get(field_name)


def optional_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    return require_mapping(value, label=label)


def optional_domain_markers(value: Any, *, label: str) -> dict[str, list[str]] | None:
    if value is None:
        return None
    mapping = require_mapping(value, label=label)
    return {required_text(domain_id, label=f"{label}.domain_id"): required_string_list(markers, label=f"{label}.{domain_id}") for domain_id, markers in mapping.items()}


def optional_string_list(value: Any, *, label: str) -> list[str] | None:
    if value is None:
        return None
    return required_string_list(value, label=label)


def required_string_list(value: Any, *, label: str) -> list[str]:
    if isinstance(value, list):
        items = [required_text(item, label=f"{label}[{index}]") for index, item in enumerate(value)]
        if not items:
            raise ValueError(f"{label} darf nicht leer sein.")
        return dedupe(items)
    if isinstance(value, str):
        parts = [item.strip() for item in LIST_SPLIT_RE.split(value) if item and item.strip()]
        if not parts:
            raise ValueError(f"{label} darf nicht leer sein.")
        return dedupe(parts)
    raise ValueError(f"{label} muss eine Liste von Strings oder ein kommagetrennter Text sein.")


def require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein Objekt sein.")
    return value


def required_projection_id(value: Any, *, label: str) -> str:
    projection_id = required_text(value, label=label)
    if not PROJECTION_ID_RE.fullmatch(projection_id):
        raise ValueError(f"{label} muss eine maschinenstabile projection_id sein.")
    return projection_id


def required_text(value: Any, *, label: str) -> str:
    return source_policy.require_text(value, label=label)


def optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def require_bool(value: Any, *, label: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{label} muss bool sein.")


def merge_unique(existing: list[str], additions: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in [*existing, *additions]:
        token = str(item).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def dedupe(values: list[str]) -> list[str]:
    return merge_unique([], values)
