from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.enums import ValueType


PROMOTION_SLOT_SCOPES = ("document",)
PROMOTION_SLOT_CARDINALITIES = ("single", "multi")
PROMOTION_SLOT_QUERY_ROLES = ("primary", "secondary", "display", "filter")

ASCII_SNAKE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def promotion_value_types() -> tuple[str, ...]:
    return ValueType.values()


def promotion_slot_name(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("slot") or "")
    if isinstance(item, str):
        return item
    return ""


def promotion_slot_names(items: Any) -> list[str]:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return []
    names = [promotion_slot_name(item) for item in items]
    return list(dict.fromkeys(name for name in names if name))


def promotion_slot_registry_errors(items: Any, *, path: str) -> list[tuple[str, str, str]]:
    if not isinstance(items, list):
        return [("function_rule_violation", "promotion_slots must be a list.", path)]
    errors: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    allowed_value_types = set(promotion_value_types())
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        if not isinstance(item, Mapping):
            errors.append(("function_rule_violation", "promotion slot definitions must be objects.", item_path))
            continue
        slot = str(item.get("slot") or "")
        if not ASCII_SNAKE_RE.match(slot):
            errors.append(("function_rule_violation", f"promotion slot must be ASCII snake_case: {slot!r}.", f"{item_path}.slot"))
        if slot in seen:
            errors.append(("function_rule_violation", f"promotion slot {slot!r} must be unique.", f"{item_path}.slot"))
        seen.add(slot)
        value_type = str(item.get("value_type") or "")
        if value_type not in allowed_value_types:
            errors.append(("enum_mismatch", f"promotion slot value_type {value_type!r} is not supported.", f"{item_path}.value_type"))
        scope = str(item.get("scope") or "")
        if scope not in PROMOTION_SLOT_SCOPES:
            errors.append(("enum_mismatch", f"promotion slot scope {scope!r} is not supported.", f"{item_path}.scope"))
        cardinality = str(item.get("cardinality") or "")
        if cardinality not in PROMOTION_SLOT_CARDINALITIES:
            errors.append(("enum_mismatch", f"promotion slot cardinality {cardinality!r} is not supported.", f"{item_path}.cardinality"))
    return errors
