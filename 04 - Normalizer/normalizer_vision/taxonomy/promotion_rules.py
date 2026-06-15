"""Helpers for dynamic Promotion Slots and Promotion Rules."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def promotion_rules_from_fields(
    fields: list[dict[str, Any]],
    *,
    include_field_codes: list[str],
    explicit_rules: Any = None,
) -> list[dict[str, Any]]:
    explicit = _rules(explicit_rules)
    if explicit:
        return explicit
    included = {str(code) for code in include_field_codes if str(code)}
    rules: list[dict[str, Any]] = []
    seen: set[str] = set()
    for field in fields:
        code = str(field.get("code") or "").strip()
        slot = str(field.get("promotion_slot") or "").strip()
        if not code or not slot or code not in included or slot in seen:
            continue
        rules.append({"slot": slot, "source_paths": [f"content.fields.{code}"]})
        seen.add(slot)
    return rules


def field_slot_map(fields: list[dict[str, Any]], *, include_field_codes: list[str] | None = None) -> dict[str, str]:
    included = {str(code) for code in include_field_codes or [] if str(code)}
    result: dict[str, str] = {}
    for field in fields:
        code = str(field.get("code") or "").strip()
        slot = str(field.get("promotion_slot") or "").strip()
        if code and slot and (not included or code in included):
            result[code] = slot
    return result


def clone_promotion_slots(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [deepcopy(dict(item)) for item in value if isinstance(item, Mapping) and item.get("slot")]


def validate_promotion_rules(
    master: Mapping[str, Any],
    projection: Mapping[str, Any],
    *,
    label: str = "projection",
    strict_source_paths: bool = False,
) -> None:
    rules = projection.get("promotion_rules")
    if not isinstance(rules, list):
        raise ValueError(f"{label}.promotion_rules muss eine Liste sein.")
    slot_names = _promotion_slot_names(master)
    field_codes = _field_codes(master)
    cell_codes = _cell_codes(master)
    included_fields = _text_set(projection.get("include_field_codes"))
    included_cells = _text_set(projection.get("include_cell_codes"))
    seen_slots: set[str] = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, Mapping):
            raise ValueError(f"{label}.promotion_rules[{index}] muss ein Objekt sein.")
        slot = str(rule.get("slot") or "").strip()
        if not slot:
            raise ValueError(f"{label}.promotion_rules[{index}].slot darf nicht leer sein.")
        if slot in seen_slots:
            raise ValueError(f"{label}.promotion_rules[{index}].slot ist doppelt: {slot}")
        if slot not in slot_names:
            raise ValueError(f"{label}.promotion_rules[{index}].slot ist nicht im Promotion Slot Registry: {slot}")
        seen_slots.add(slot)
        source_paths = rule.get("source_paths")
        if not isinstance(source_paths, list) or not source_paths:
            raise ValueError(f"{label}.promotion_rules[{index}].source_paths darf nicht leer sein.")
        for path_index, source_path in enumerate(source_paths):
            _validate_source_path(
                str(source_path or "").strip(),
                label=f"{label}.promotion_rules[{index}].source_paths[{path_index}]",
                field_codes=field_codes,
                cell_codes=cell_codes,
                included_fields=included_fields,
                included_cells=included_cells,
                strict_source_paths=strict_source_paths,
            )


def _promotion_slot_names(master: Mapping[str, Any]) -> set[str]:
    slots = master.get("promotion_slots")
    if not isinstance(slots, list):
        return set()
    return {
        slot
        for item in slots
        if isinstance(item, Mapping) and (slot := str(item.get("slot") or "").strip())
    }


def _field_codes(master: Mapping[str, Any]) -> set[str]:
    fields = master.get("field_codes")
    if isinstance(fields, Mapping):
        return {str(key) for key in fields if str(key)}
    if isinstance(fields, list):
        return {
            code
            for item in fields
            if isinstance(item, Mapping) and (code := str(item.get("code") or "").strip())
        }
    return set()


def _cell_codes(master: Mapping[str, Any]) -> set[str]:
    cells = master.get("cell_codes")
    if isinstance(cells, Mapping):
        return {str(key) for key in cells if str(key)}
    if isinstance(cells, list):
        return {
            code
            for item in cells
            if isinstance(item, Mapping) and (code := str(item.get("code") or "").strip())
        }
    return set()


def _text_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {text for item in value if (text := str(item or "").strip())}


def _rules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rules: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping) or not item.get("slot"):
            continue
        rule = deepcopy(dict(item))
        source_paths = rule.get("source_paths")
        if isinstance(source_paths, list):
            normalized_paths = [path for child in source_paths if (path := str(child or "").strip())]
            if not normalized_paths:
                continue
            rule["source_paths"] = normalized_paths
        rules.append(rule)
    return rules


def _validate_source_path(
    source_path: str,
    *,
    label: str,
    field_codes: set[str],
    cell_codes: set[str],
    included_fields: set[str],
    included_cells: set[str],
    strict_source_paths: bool,
) -> None:
    if not source_path:
        raise ValueError(f"{label} darf nicht leer sein.")
    if source_path.startswith("content.fields."):
        if not strict_source_paths:
            return
        field_code = _field_code_from_source_path(source_path)
        if field_code not in field_codes:
            raise ValueError(f"{label} referenziert unbekannten Field Code: {field_code}")
        if strict_source_paths and field_code not in included_fields:
            raise ValueError(f"{label} referenziert nicht inkludierten Field Code: {field_code}")
        return
    if source_path.startswith("content.rows[*]."):
        if source_path.startswith("content.rows[*].cells."):
            raise ValueError(f"{label} hat ungueltigen Source Path: {source_path}")
        if not strict_source_paths:
            return
        cell_code = _cell_code_from_row_source_path(source_path)
        if cell_code not in cell_codes:
            raise ValueError(f"{label} referenziert unbekannten Cell Code: {cell_code}")
        if strict_source_paths and cell_code not in included_cells:
            raise ValueError(f"{label} referenziert nicht inkludierten Cell Code: {cell_code}")
        return
    if source_path.startswith("context.") or source_path.startswith("content.structure."):
        return
    raise ValueError(f"{label} hat ungueltigen Source Path: {source_path}")


def _field_code_from_source_path(source_path: str) -> str:
    rest = source_path.removeprefix("content.fields.")
    return rest.split(".", 1)[0].split("[", 1)[0].strip()


def _cell_code_from_row_source_path(source_path: str) -> str:
    rest = source_path.removeprefix("content.rows[*].")
    return rest.split(".", 1)[0].split("[", 1)[0].strip()
