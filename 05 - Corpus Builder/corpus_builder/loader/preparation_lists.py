"""List normalization helpers for loader payload preparation."""

from __future__ import annotations

from .policy import is_non_empty
from .types import JsonDict, NORMALIZED_LIST_KEYS


def normalize_name_list(values: object, list_name: str) -> list[str]:
    keys = NORMALIZED_LIST_KEYS[list_name]
    normalized: list[str] = []
    if not isinstance(values, list):
        return normalized
    for value in values:
        if isinstance(value, dict):
            picked = next((str(value[key]).strip() for key in keys if is_non_empty(value.get(key))), None)
            if picked:
                normalized.append(picked)
        elif is_non_empty(value):
            normalized.append(str(value).strip())
    return normalized


def merge_name_lists(primary: list[str], fallback: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*primary, *fallback]:
        marker = str(value).strip().casefold()
        if marker not in seen:
            seen.add(marker)
            merged.append(value)
    return merged


def preferred_name_list(preferred_json: JsonDict, fallback_json: JsonDict, key: str, context_fn) -> list[str]:
    preferred = normalize_name_list(context_fn(preferred_json).get(key), key)
    return preferred or normalize_name_list(context_fn(fallback_json).get(key), key)
