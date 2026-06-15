from __future__ import annotations

from typing import Any, Mapping


def allowed_codes_by_section(input_payload: Any) -> dict[str, tuple[str, ...]]:
    allowed_codes = find_mapping(input_payload, "allowed_codes")
    if not isinstance(allowed_codes, Mapping):
        return {}
    result: dict[str, tuple[str, ...]] = {}
    for key, value in allowed_codes.items():
        if isinstance(value, list):
            result[str(key)] = tuple(str(item) for item in value if str(item))
    return result


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
