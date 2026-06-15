from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.paths import utc_iso


def build_trace_context(
    *,
    trace_id: str,
    workflow_run_id: str,
    workflow_tool: str,
    started_by: str,
    root_target_identity_ref: Mapping[str, Any] | str,
    state_root_ref: Mapping[str, Any] | str,
    parent_trace_id: str | None = None,
    active_recovery_event_id: str | None = None,
    active_mirror_event_id: str | None = None,
    active_support_bundle_id: str | None = None,
    related_pipeline_run_id: str | None = None,
    related_analysis_run_ids: tuple[Mapping[str, Any] | str, ...] = (),
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "debug.trace_context.v1",
        "trace_id": trace_id,
        "workflow_run_id": workflow_run_id,
        "workflow_tool": workflow_tool,
        "created_at": utc_iso(),
        "started_by": started_by,
        "root_target_identity_ref": dict(root_target_identity_ref) if isinstance(root_target_identity_ref, Mapping) else str(root_target_identity_ref),
        "state_root_ref": dict(state_root_ref) if isinstance(state_root_ref, Mapping) else str(state_root_ref),
    }
    if parent_trace_id is not None:
        payload["parent_trace_id"] = parent_trace_id
    if active_recovery_event_id is not None:
        payload["active_recovery_event_id"] = active_recovery_event_id
    if active_mirror_event_id is not None:
        payload["active_mirror_event_id"] = active_mirror_event_id
    if active_support_bundle_id is not None:
        payload["active_support_bundle_id"] = active_support_bundle_id
    if related_pipeline_run_id is not None:
        payload["related_pipeline_run_id"] = related_pipeline_run_id
    if related_analysis_run_ids:
        payload["related_analysis_run_ids"] = [
            dict(item) if isinstance(item, Mapping) else str(item)
            for item in related_analysis_run_ids
        ]
    return payload
