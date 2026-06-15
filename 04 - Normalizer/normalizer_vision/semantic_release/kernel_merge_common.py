from __future__ import annotations

from typing import Any, Mapping, Sequence

from .kernel_candidate import stable_hash


def projection_merge_mode(value: str) -> str:
    return value if value == "merge_to_single_projection" else "preserve_source_projections"


def merged_text_list(refs: Sequence[Mapping[str, Any]], key: str) -> list[str]:
    values: set[str] = set()
    for ref in refs:
        raw = ref.get(key)
        if isinstance(raw, list):
            values.update(str(item).strip() for item in raw if str(item).strip())
        elif isinstance(raw, str) and raw.strip():
            values.add(raw.strip())
    return sorted(values)


def first_text(refs: Sequence[Mapping[str, Any]], key: str) -> str:
    for ref in refs:
        text = str(ref.get(key) or "").strip()
        if text:
            return text
    return ""


def collision(collision_class: str, merge_run_id: str, identifier: str, source_ref: Mapping[str, Any]) -> dict[str, Any]:
    collision_id = f"col_{stable_hash(f'{merge_run_id}:{collision_class}:{identifier}')[:12]}"
    return {
        "collision_id": collision_id,
        "collision_class": collision_class,
        "source_refs": [dict(source_ref)],
        "target_ref": {"identifier": identifier},
        "default_policy": "keep_first",
        "resolution_owner": "kernel_dialog",
        "resolution_status": "requires_user_choice",
        "selected_resolution": None,
        "requires_user_choice": True,
        "blocks_activation": True,
        "diagnostics": [{"identifier": identifier}],
    }
