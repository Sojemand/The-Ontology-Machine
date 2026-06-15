from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from semantic_control_kernel.policy.promotion_slots import promotion_slot_names
from semantic_control_kernel.validation.llm.common_traversal import iter_key_values

ValidationError = tuple[str, str, str]

_ASCII_SNAKE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_PROJECTION_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]*$")
_PROMOTION_SOURCE_PATH_PREFIXES = (
    "context.",
    "content.fields.",
    "content.rows[*].",
    "content.structure.",
)
_ROW_CELL_SOURCE_PREFIX = "content.rows[*]."
_STATUS_ALIASES = {
    "candidate": "draft",
    "proposed": "draft",
    "pending": "draft",
    "new": "draft",
    "enabled": "active",
}


def ref_mismatch_errors(*, actual: Mapping[str, Any], expected: Mapping[str, Any], keys: Sequence[str], code: str, path: str) -> list[ValidationError]:
    errors = []
    for key in keys:
        if key not in expected:
            continue
        if key not in actual:
            errors.append((code, f"{path}.{key} must be present and match prompt input.", f"{path}.{key}"))
        elif actual[key] != expected[key]:
            errors.append((code, f"{path}.{key} must match prompt input.", f"{path}.{key}"))
    return errors


def subset_errors(values: Sequence[Any], allowed: Sequence[str], path: str) -> list[ValidationError]:
    if not allowed:
        return []
    allowed_set = set(str(value) for value in allowed)
    for value in values:
        text = str(value)
        if text not in allowed_set:
            return [("unknown_taxonomy_code", f"{path} contains unknown taxonomy code {text!r}.", path)]
    return []


def code_list_errors(values: Sequence[Any], path: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        code = str(value)
        if code != "other" and not _ASCII_SNAKE_RE.match(code):
            errors.append(("function_rule_violation", f"candidate code must be ASCII snake_case: {code!r}.", f"{path}[{index}]"))
        if code in seen:
            errors.append(("function_rule_violation", f"candidate code {code!r} must be unique.", f"{path}[{index}]"))
        seen.add(code)
    return errors


def promotion_slot_errors(value: Mapping[str, Any], context: Any, path: str, *, require_registry: bool = False) -> list[ValidationError]:
    if not context.allowed_promotion_slots:
        if require_registry and getattr(context, "input_payload", None) is not None:
            return [("function_rule_violation", "promotion slot registry is required for projection validation.", path)]
        return []
    allowed = set(str(item) for item in context.allowed_promotion_slots)
    return [
        ("function_rule_violation", f"promotion slot {slot!r} is not allowed by the prompt input.", slot_path)
        for slot_path, slot in iter_key_values(value, "slot", path)
        if isinstance(slot, str) and slot and slot not in allowed
    ]


def field_promotion_slot_errors(value: Any, allowed_slots: Sequence[str], path: str) -> list[ValidationError]:
    allowed = set(str(item) for item in allowed_slots if str(item))
    if not allowed:
        return []
    return [
        ("function_rule_violation", f"promotion slot {slot!r} is not defined by taxonomy_core.promotion_slots.", slot_path)
        for slot_path, slot in iter_key_values(value, "promotion_slot", path)
        if isinstance(slot, str) and slot and slot not in allowed
    ]


def promotion_source_path_errors(value: Any, path: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for source_path_path, source_path in iter_key_values(value, "source_paths", path):
        if not isinstance(source_path, list):
            continue
        if not any(isinstance(item, str) and item.strip() for item in source_path):
            errors.append(("invalid_promotion_path", "promotion source_paths must not be empty; omit unmapped promotion rules.", source_path_path))
            continue
        for item in source_path:
            if not isinstance(item, str) or not item.startswith(_PROMOTION_SOURCE_PATH_PREFIXES):
                errors.append(("invalid_promotion_path", "promotion source_paths must be compact Normalizer semantic paths.", source_path_path))
            elif item.startswith("content.rows[*].cells."):
                errors.append(("invalid_promotion_path", "row promotion source paths use cell codes directly, not a cells wrapper.", source_path_path))
    return errors


def promotion_source_field_errors(value: Any, *, known_field_codes: Sequence[str], included_field_codes: Sequence[str] = (), path: str) -> list[ValidationError]:
    return _promotion_source_code_errors(
        value,
        known_codes=known_field_codes,
        included_codes=included_field_codes,
        path=path,
        prefix="content.fields.",
        unknown_message="promotion source field {code!r} is not in the taxonomy.",
        excluded_message="promotion source field {code!r} is not included by the projection.",
    )


def promotion_source_cell_errors(value: Any, *, known_cell_codes: Sequence[str], included_cell_codes: Sequence[str] = (), path: str) -> list[ValidationError]:
    return _promotion_source_code_errors(
        value,
        known_codes=known_cell_codes,
        included_codes=included_cell_codes,
        path=path,
        prefix=_ROW_CELL_SOURCE_PREFIX,
        skip_prefix="content.rows[*].cells.",
        unknown_message="promotion source cell {code!r} is not in the taxonomy.",
        excluded_message="promotion source cell {code!r} is not included by the projection.",
    )


def _promotion_source_code_errors(value: Any, *, known_codes: Sequence[str], included_codes: Sequence[str], path: str, prefix: str, unknown_message: str, excluded_message: str, skip_prefix: str = "") -> list[ValidationError]:
    known = set(str(item) for item in known_codes if str(item))
    included = set(str(item) for item in included_codes if str(item))
    errors: list[ValidationError] = []
    for source_path_path, source_paths in iter_key_values(value, "source_paths", path):
        if not isinstance(source_paths, list):
            continue
        for source_path in source_paths:
            if not isinstance(source_path, str) or not source_path.startswith(prefix) or (skip_prefix and source_path.startswith(skip_prefix)):
                continue
            code = source_path.removeprefix(prefix).split(".", 1)[0]
            if known and code not in known:
                errors.append(("unknown_taxonomy_code", unknown_message.format(code=code), source_path_path))
            elif included and code not in included:
                errors.append(("unknown_taxonomy_code", excluded_message.format(code=code), source_path_path))
    return errors


def promotion_slot_names_from_registry(value: Any) -> list[str]:
    return promotion_slot_names(value)
