from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.merge import MergeWorkflowBlocker


def require_fields(payload: Mapping[str, Any], fields: Sequence[str], contract: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise ValueError(f"{contract} missing required field(s): {', '.join(missing)}")


def require_non_empty(payload: Mapping[str, Any], fields: Sequence[str], contract: str) -> None:
    empty = [field for field in fields if not str(payload.get(field, "")).strip()]
    if empty:
        raise ValueError(f"{contract} requires non-empty field(s): {', '.join(empty)}")


def target_conflict(field_name: str) -> MergeWorkflowBlocker:
    return MergeWorkflowBlocker(
        blocker_code="target_conflict",
        step_id="source_selection",
        function_or_route="database_merge_additive_only",
        recovery_state_class="target_identity_changed",
        user_visible_summary=f"Merge {field_name} must not be one of the selected sources.",
    )


def norm_path(value: object) -> str:
    return str(value or "").replace("\\", "/").rstrip("/").casefold()


def stable_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: stable_payload(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [stable_payload(item) for item in value]
    return value
