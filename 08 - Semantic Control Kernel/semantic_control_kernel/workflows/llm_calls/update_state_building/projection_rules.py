from __future__ import annotations

import re
from typing import Any, Mapping

from semantic_control_kernel.policy.promotion_slots import promotion_slot_names
from semantic_control_kernel.workflows.llm_calls.update_state_building.errors import UpdateStateBuilderError

_PROJECTION_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]*$")
_ALLOWED_PROMOTION_SOURCE_PATH_PREFIXES = (
    "context.",
    "content.fields.",
    "content.rows[*].",
    "content.structure.",
)
_ROW_CELL_SOURCE_PREFIX = "content.rows[*]."


def _validate_projection_precursors(projections: list[Mapping[str, Any]], real_taxonomy_proof: Mapping[str, Any]) -> None:
    seen: set[str] = set()
    promotion_slots = _required_promotion_slots(real_taxonomy_proof)
    for projection in projections:
        projection_id = str(projection.get("projection_id", ""))
        if not _PROJECTION_ID_RE.match(projection_id):
            raise UpdateStateBuilderError(f"invalid projection_id {projection_id!r}.")
        if projection_id in seen:
            raise UpdateStateBuilderError(f"duplicate projection_id {projection_id!r}.")
        seen.add(projection_id)
        _validate_projection_include_lists(projection, real_taxonomy_proof)
        _validate_promotion_rule_lists(
            projection,
            promotion_slots=promotion_slots,
            allowed_codes=_allowed_codes(real_taxonomy_proof),
            included_field_codes={str(code) for code in (projection.get("include_field_codes") or ()) if isinstance(code, str)},
            included_cell_codes={str(code) for code in (projection.get("include_cell_codes") or ()) if isinstance(code, str)},
        )


def _validate_projection_include_lists(value: Mapping[str, Any], real_taxonomy_proof: Mapping[str, Any]) -> None:
    allowed_codes = set(str(code) for code in real_taxonomy_proof.get("allowed_codes", ()))
    fallback_codes = set(str(code) for code in real_taxonomy_proof.get("fallback_codes", ("other",)))
    for key, child in value.items():
        if not isinstance(child, list):
            continue
        if _is_projection_domain_key(key):
            _reject_unknown_projection_codes(key, child, allowed_codes)
        elif _is_full_projection_include_key(key):
            if fallback_codes and not fallback_codes.intersection(str(code) for code in child):
                raise UpdateStateBuilderError(f"{key} must include configured fallback.")
            _reject_unknown_projection_codes(key, child, allowed_codes)
        elif _is_projection_delta_include_key(key):
            if key.startswith("remove_") and fallback_codes.intersection(str(code) for code in child):
                raise UpdateStateBuilderError(f"{key} cannot remove configured fallback.")
            _reject_unknown_projection_codes(key, child, allowed_codes)


def _reject_unknown_projection_codes(key: str, values: list[Any], allowed_codes: set[str]) -> None:
    unknown = [str(code) for code in values if allowed_codes and str(code) not in allowed_codes]
    if unknown:
        raise UpdateStateBuilderError(f"{key} contains unknown taxonomy code {unknown[0]!r}.")


def _required_promotion_slots(real_taxonomy_proof: Mapping[str, Any]) -> set[str]:
    slots = set(promotion_slot_names(real_taxonomy_proof.get("promotion_slots", ())))
    if not slots:
        raise UpdateStateBuilderError("promotion slot registry is missing.")
    return slots


def _allowed_codes(real_taxonomy_proof: Mapping[str, Any]) -> set[str]:
    return set(str(code) for code in real_taxonomy_proof.get("allowed_codes", ()) if str(code))


def _validate_promotion_rule_lists(
    value: Mapping[str, Any],
    *,
    promotion_slots: set[str],
    allowed_codes: set[str],
    included_field_codes: set[str],
    included_cell_codes: set[str],
) -> None:
    for rules in _iter_promotion_rule_lists(value):
        for rule in rules:
            if not isinstance(rule, Mapping):
                continue
            slot = str(rule.get("slot") or "")
            if slot not in promotion_slots:
                raise UpdateStateBuilderError(f"promotion slot {slot!r} is not configured.")
            source_paths = rule.get("source_paths", [])
            if not isinstance(source_paths, list):
                continue
            for source_path in source_paths:
                text = str(source_path)
                if not text.startswith(_ALLOWED_PROMOTION_SOURCE_PATH_PREFIXES):
                    raise UpdateStateBuilderError(f"promotion source path {text!r} is invalid.")
                if text.startswith("content.fields."):
                    field_code = text.removeprefix("content.fields.").split(".", 1)[0]
                    if allowed_codes and field_code not in allowed_codes:
                        raise UpdateStateBuilderError(f"promotion source field {field_code!r} is not in the taxonomy.")
                    if included_field_codes and field_code not in included_field_codes:
                        raise UpdateStateBuilderError(f"promotion source field {field_code!r} is not included by the projection.")
                if text.startswith("content.rows[*]."):
                    if text.startswith("content.rows[*].cells."):
                        raise UpdateStateBuilderError(f"promotion source path {text!r} is invalid.")
                    cell_code = text.removeprefix(_ROW_CELL_SOURCE_PREFIX).split(".", 1)[0]
                    if allowed_codes and cell_code not in allowed_codes:
                        raise UpdateStateBuilderError(f"promotion source cell {cell_code!r} is not in the taxonomy.")
                    if included_cell_codes and cell_code not in included_cell_codes:
                        raise UpdateStateBuilderError(f"promotion source cell {cell_code!r} is not included by the projection.")


def _iter_promotion_rule_lists(value: Mapping[str, Any]):
    for key in (
        "promotion_rules",
        "add_promotion_rules",
        "set_promotion_rules",
        "remove_promotion_rules",
    ):
        rules = value.get(key)
        if isinstance(rules, list):
            yield rules


def _is_projection_domain_key(key: str) -> bool:
    return key in {"domain_ids", "add_domain_ids", "set_domain_ids", "remove_domain_ids"}


def _is_full_projection_include_key(key: str) -> bool:
    return key.startswith("include_") or key.startswith("set_include_")


def _is_projection_delta_include_key(key: str) -> bool:
    return key.startswith("add_include_") or key.startswith("remove_include_")
