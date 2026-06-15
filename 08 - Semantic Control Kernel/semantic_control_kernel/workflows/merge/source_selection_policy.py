from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.merge import (
    PROJECTION_MERGE_MODE_DEFAULT,
    PROJECTION_MERGE_MODE_SINGLE,
    PROJECTION_MERGE_MODE_VALUES,
    MergeWorkflowBlocker,
)
from semantic_control_kernel.validation.merge_validation import validate_no_mixed_sources, validate_target_not_source


def classify_merge_route(source_states: Sequence[str]) -> str | MergeWorkflowBlocker:
    states = set(source_states)
    if states == {"empty"}:
        return "empty_databases_merge_path"
    if states <= {"empty", "filled"} and "filled" in states:
        return "filled_databases_merge_path"
    return MergeWorkflowBlocker(
        blocker_code="source_state_unknown",
        step_id="classifying_merge_route",
        function_or_route="database_merge_additive_only",
        recovery_state_class="none",
        user_visible_summary="Merge source states must be empty or filled before additive merge can run.",
        diagnostics=({"source_states": sorted(states)},),
    )


def route_blocker_for_selection(selection: Mapping[str, Any]) -> MergeWorkflowBlocker | None:
    blocker = validate_no_mixed_sources(selection)
    if blocker is not None:
        return blocker
    return validate_target_not_source(selection)


def projection_merge_mode_blocker(selection: Mapping[str, Any]) -> MergeWorkflowBlocker | None:
    mode = normalize_projection_merge_mode(selection.get("projection_merge_mode"))
    if mode != PROJECTION_MERGE_MODE_SINGLE:
        return None
    if str(selection.get("merge_route") or "") == "empty_databases_merge_path":
        return None
    return MergeWorkflowBlocker(
        blocker_code="projection_merge_mode_not_supported",
        step_id="validating_projection_merge_mode",
        function_or_route="database_merge_additive_only",
        recovery_state_class="none",
        user_visible_summary="Single-projection merge is only supported for empty database merges. Keep source projections for filled database merges.",
        diagnostics=({"projection_merge_mode": mode, "merge_route": str(selection.get("merge_route") or "")},),
    )


def normalize_projection_merge_mode(value: object) -> str:
    text = str(value or "").strip()
    if text in PROJECTION_MERGE_MODE_VALUES:
        return text
    return PROJECTION_MERGE_MODE_DEFAULT
