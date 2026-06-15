from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.types.merge import PROJECTION_MERGE_MODE_DEFAULT, DatabaseMergeSelection, MergeWorkflowBlocker
from semantic_control_kernel.validation.merge_validation import selection_fingerprint, validate_selection_contract
from semantic_control_kernel.workflows.merge.source_identity import selection_sources_stable
from semantic_control_kernel.workflows.merge.source_selection_builder import build_database_merge_selection


def resume_database_merge_selection(
    *,
    selected_sources: Sequence[Mapping[str, Any]],
    target_artifact_root: str | Path,
    selected_by_interaction_id: str,
    merge_run_id: str,
    target_database_path: str | Path | None = None,
    projection_merge_mode: str = PROJECTION_MERGE_MODE_DEFAULT,
) -> DatabaseMergeSelection | MergeWorkflowBlocker | None:
    existing = load_existing_database_merge_selection(target_artifact_root, merge_run_id)
    if existing is None:
        return None
    candidate = build_database_merge_selection(
        selected_sources=selected_sources,
        target_artifact_root=target_artifact_root,
        target_database_path=target_database_path,
        selected_by_interaction_id=selected_by_interaction_id,
        merge_run_id=merge_run_id,
        created_at=str(existing.get("created_at", "")),
        projection_merge_mode=projection_merge_mode,
    )
    if not isinstance(candidate, DatabaseMergeSelection):
        return _stale_selection_blocker("current source selection no longer satisfies the persisted merge selection contract")
    candidate_payload = candidate.to_dict()
    comparable_fields = ("merge_route", "target_artifact_root", "target_database_path", "projection_merge_mode")
    if any(str(existing.get(field, "")) != str(candidate_payload.get(field, "")) for field in comparable_fields):
        return _stale_selection_blocker("target route or target identity changed after selection")
    if not selection_sources_stable(existing, candidate_payload):
        return _stale_selection_blocker("source database identity, path, state or fingerprint changed after selection")
    return DatabaseMergeSelection(_enrich_existing_selection(existing, candidate_payload))


def load_existing_database_merge_selection(target_artifact_root: str | Path, merge_run_id: str) -> dict[str, Any] | None:
    path = Path(target_artifact_root) / "Documents" / "logs" / "merge_runs" / require_state_id("merge_run_id", merge_run_id) / "merge_selection.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Persisted merge selection cannot be read: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Persisted merge selection is not an object.")
    validate_selection_contract(payload)
    return dict(payload)


def _stale_selection_blocker(reason: str) -> MergeWorkflowBlocker:
    return MergeWorkflowBlocker(
        blocker_code="target_identity_changed",
        step_id="classifying_merge_route",
        function_or_route="database_merge_additive_only",
        recovery_state_class="target_identity_changed",
        user_visible_summary="Persisted merge selection is stale and the merge must be reselected.",
        diagnostics=({"reason": reason},),
    )


def _enrich_existing_selection(existing: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(existing)
    existing_sources = [dict(item) for item in payload.get("source_databases", []) if isinstance(item, Mapping)]
    candidate_by_id = {
        str(item.get("source_database_id") or ""): item
        for item in candidate.get("source_databases", [])
        if isinstance(item, Mapping)
    }
    changed = False
    for source in existing_sources:
        if isinstance(source.get("source_release_ref"), Mapping) and source["source_release_ref"]:
            continue
        candidate_source = candidate_by_id.get(str(source.get("source_database_id") or ""))
        if isinstance(candidate_source, Mapping) and isinstance(candidate_source.get("source_release_ref"), Mapping):
            source["source_release_ref"] = dict(candidate_source["source_release_ref"])
            changed = True
    if changed:
        payload["source_databases"] = existing_sources
        payload["selection_fingerprint"] = selection_fingerprint(payload)
    return payload
