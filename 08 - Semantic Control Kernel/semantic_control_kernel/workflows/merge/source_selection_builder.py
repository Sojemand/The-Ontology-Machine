from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.merge import (
    PROJECTION_MERGE_MODE_DEFAULT,
    DatabaseMergeSelection,
    MergeWorkflowBlocker,
)
from semantic_control_kernel.validation.merge_validation import (
    selection_fingerprint,
    validate_selection_contract,
    validate_source_count,
    validate_target_not_source,
)
from semantic_control_kernel.workflows.merge.source_identity import build_source_descriptor
from semantic_control_kernel.workflows.merge.source_selection_policy import (
    classify_merge_route,
    normalize_projection_merge_mode,
)
from semantic_control_kernel.workflows.merge.source_selection_target import resolve_merge_target_database_path


def build_database_merge_selection(
    *,
    selected_sources: Sequence[Mapping[str, Any]],
    target_artifact_root: str | Path,
    selected_by_interaction_id: str,
    target_database_path: str | Path | None = None,
    merge_run_id: str | None = None,
    created_at: str | None = None,
    projection_merge_mode: str = PROJECTION_MERGE_MODE_DEFAULT,
) -> DatabaseMergeSelection | MergeWorkflowBlocker:
    blocker = validate_source_count(selected_sources)
    if blocker is not None:
        return blocker
    timestamp = created_at or utc_iso()
    descriptors = [
        build_source_descriptor(source, ordinal=index, selection_timestamp=timestamp)
        for index, source in enumerate(selected_sources, start=1)
    ]
    route = classify_merge_route([descriptor.source_state for descriptor in descriptors])
    if isinstance(route, MergeWorkflowBlocker):
        return route
    target_root = Path(target_artifact_root).resolve(strict=False)
    try:
        target_db = resolve_merge_target_database_path(target_root, target_database_path)
    except ValueError as exc:
        return MergeWorkflowBlocker(
            blocker_code="target_path_escape",
            step_id="source_selection",
            function_or_route="database_merge_additive_only",
            recovery_state_class="target_identity_changed",
            user_visible_summary=str(exc),
        )
    mode = normalize_projection_merge_mode(projection_merge_mode)
    payload = {
        "schema_version": DatabaseMergeSelection.SCHEMA_VERSION,
        "created_at": timestamp,
        "merge_route": route,
        "merge_run_id": require_state_id("merge_run_id", merge_run_id or generate_id("merge_run_id")),
        "projection_merge_mode": mode,
        "selected_by_interaction_id": selected_by_interaction_id,
        "source_databases": [descriptor.to_selection_entry() for descriptor in descriptors],
        "target_artifact_root": str(target_root),
        "target_database_path": str(target_db),
        "selection_fingerprint": "",
    }
    payload["selection_fingerprint"] = selection_fingerprint(payload)
    target_blocker = validate_target_not_source(payload)
    if target_blocker is not None:
        return target_blocker
    validate_selection_contract(payload)
    return DatabaseMergeSelection(payload)
