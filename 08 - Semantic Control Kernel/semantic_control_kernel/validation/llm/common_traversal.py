from __future__ import annotations

from typing import Any, Mapping, Sequence


def action_bank_entries(action_bank: Any) -> list[Mapping[str, Any]]:
    if isinstance(action_bank, Mapping) and isinstance(action_bank.get("actions"), list):
        return [item for item in action_bank["actions"] if isinstance(item, Mapping)]
    if isinstance(action_bank, list):
        return [item for item in action_bank if isinstance(item, Mapping)]
    return []


def include_key_to_section(key: str) -> str:
    return {
        "include_document_types": "document_types",
        "include_categories": "categories",
        "include_subcategories": "subcategories",
        "include_field_codes": "field_codes",
        "include_row_types": "row_types",
        "include_cell_codes": "cell_codes",
    }.get(key, "")


def domain_marker_ids(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return [str(key) for key in value]
    if isinstance(value, list):
        ids: list[str] = []
        for item in value:
            if isinstance(item, Mapping) and isinstance(item.get("domain_id"), str):
                ids.append(str(item["domain_id"]))
        return ids
    return []


def operation_group(action: Mapping[str, Any]) -> str:
    return str(action.get("operation_group") or action.get("operation") or action.get("action_family") or "")


def iter_code_values(value: Any, path: str = ""):
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "code" and isinstance(child, str):
                yield child_path, child
            else:
                yield from iter_code_values(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_code_values(child, f"{path}[{index}]")


def iter_key_values(value: Any, wanted_key: str, path: str = "$"):
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == wanted_key:
                yield child_path, child
            else:
                yield from iter_key_values(child, wanted_key, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_key_values(child, wanted_key, f"{path}[{index}]")


def first_mapping_at_keys(value: Any, keys: Sequence[str]) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        for key in keys:
            child = value.get(key)
            if isinstance(child, Mapping):
                return child
        for child in value.values():
            found = first_mapping_at_keys(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = first_mapping_at_keys(child, keys)
            if found is not None:
                return found
    return None


def find_mapping(value: Any, key: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        child = value.get(key)
        if isinstance(child, Mapping):
            return child
        for nested in value.values():
            found = find_mapping(nested, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = find_mapping(nested, key)
            if found is not None:
                return found
    return None


def find_first_list(value: Any, key: str) -> list[Any] | None:
    if isinstance(value, Mapping):
        child = value.get(key)
        if isinstance(child, list):
            return child
        for nested in value.values():
            found = find_first_list(nested, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = find_first_list(nested, key)
            if found is not None:
                return found
    return None


def unique(values):
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            yield value
