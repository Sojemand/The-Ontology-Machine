from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.surface.client_frontend_bridge import list_client_frontend_events


def event_belongs_to_phase20_snapshot(
    event: Mapping[str, Any],
    *,
    workflow_run_ids: set[str],
    mirror_event_ids: set[str],
    interaction_request_ids: set[str],
) -> bool:
    kind = str(event.get("frontend_event_kind") or "")
    if kind == "interaction_request":
        request = event.get("interaction_request")
        return isinstance(request, Mapping) and str(request.get("interaction_request_id") or "") in interaction_request_ids
    if kind == "progress_event":
        progress = event.get("progress_event")
        return isinstance(progress, Mapping) and str(progress.get("workflow_run_id") or "") in workflow_run_ids
    if kind in {"mirror_event", "tool_availability"}:
        return str(event.get("mirror_event_id") or "") in mirror_event_ids
    return False


def list_all_client_frontend_events(
    base_request: Mapping[str, Any],
    *,
    state_paths: StatePaths,
    page_limit: int = 200,
) -> tuple[list[Mapping[str, Any]], str]:
    events: list[Mapping[str, Any]] = []
    cursor: str | None = None
    final_cursor = "0"
    while True:
        request_payload = dict(base_request)
        request_payload["limit"] = page_limit
        if cursor:
            request_payload["cursor"] = cursor
        batch = list_client_frontend_events(request_payload, state_paths=state_paths)
        page_events = [event for event in batch.get("events", []) if isinstance(event, Mapping)]
        events.extend(page_events)
        next_cursor = str(batch.get("cursor") or final_cursor)
        final_cursor = next_cursor
        if len(page_events) < page_limit:
            break
        if next_cursor == cursor:
            break
        cursor = next_cursor
    return events, final_cursor
