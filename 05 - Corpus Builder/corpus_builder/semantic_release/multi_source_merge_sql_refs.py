from __future__ import annotations

import json
from typing import Any, Mapping

from .multi_source_merge_types import stable_hash


def merged_id(prefix: str, *, merge_run_id: str, source_database_id: str, source_id: object) -> str:
    return f"{prefix}_{stable_hash(f'{merge_run_id}:{source_database_id}:{source_id}')[:16]}"


def stringify_map(mapping: Mapping[object, object]) -> dict[str, str]:
    return {str(key): str(value) for key, value in mapping.items() if key is not None and value is not None}


def rewrite_json_text(value: object, replacements: Mapping[str, str]) -> object:
    if value is None or not replacements:
        return value
    text = str(value)
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return replacements.get(text, value)
    return json.dumps(rewrite_json_refs(parsed, replacements), ensure_ascii=False, separators=(",", ":"))


def rewrite_json_refs(value: Any, replacements: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: rewrite_json_refs(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_json_refs(item, replacements) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    if isinstance(value, int):
        return replacements.get(str(value), value)
    return value


def merged_ref_id(ref_type: object, ref_id: object, ref_maps: Mapping[str, Mapping[str, str]]) -> str | None:
    ref_text = str(ref_id or "")
    if not ref_text:
        return None
    ref_map = ref_maps.get(str(ref_type or ""))
    if ref_map is None:
        return ref_text
    return ref_map.get(ref_text)

