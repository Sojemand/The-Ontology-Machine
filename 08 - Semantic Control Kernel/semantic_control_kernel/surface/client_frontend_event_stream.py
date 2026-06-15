from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from semantic_control_kernel.repository.event_store import MirrorEventStore, ProgressEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.records import MirrorToolAvailability
from semantic_control_kernel.types.events import ClientFrontendEvent, ClientFrontendEventBatch
from semantic_control_kernel.validation.client_frontend_bridge_validation import (
    validate_client_events_request,
    validate_client_frontend_event_batch,
)
from semantic_control_kernel.surface.client_frontend_event_scope import (
    FrontendEventScope,
    file_mtime_iso,
    frontend_event_scope,
    latest_reset_created_at,
    mapping_is_after_reset_boundary,
    timestamp_is_after_reset_boundary,
)


def list_client_frontend_events(
    request: Mapping[str, Any],
    *,
    state_paths: StatePaths,
) -> dict[str, Any]:
    validate_client_events_request(request)
    events, live_progress_workflow_run_ids = collect_client_frontend_events(state_paths)
    limit = int(request.get("limit") or 50)
    start = cursor_to_index(request.get("cursor"))
    if start > len(events):
        start = max(0, len(events) - limit)
    selected_window = events[start : start + limit]
    selected = with_replayed_live_state_events(
        events,
        selected_window,
        progress_replay_workflow_run_ids=live_progress_workflow_run_ids,
    )
    payload = {
        "schema_version": ClientFrontendEventBatch.SCHEMA_VERSION,
        "cursor": str(start + len(selected_window)),
        "events": [event.to_dict() for event in selected],
    }
    validate_client_frontend_event_batch(payload)
    return payload


def collect_client_frontend_events(state_paths: StatePaths) -> tuple[list[ClientFrontendEvent], frozenset[str]]:
    pending_requests = pending_interaction_payloads(state_paths)
    reset_boundary = latest_reset_created_at(state_paths)
    scope = frontend_event_scope(state_paths, pending_requests, reset_boundary=reset_boundary)
    events: list[ClientFrontendEvent] = []
    events.extend(interaction_request_events(pending_requests))
    events.extend(progress_events(state_paths, scope))
    events.extend(mirror_events(state_paths, scope, reset_boundary=reset_boundary))
    events.extend(tool_availability_events(state_paths, reset_boundary=reset_boundary))
    events.sort(key=lambda event: (str(event.payload.get("created_at") or ""), str(event.payload.get("frontend_event_id") or "")))
    live_progress_workflow_run_ids = frozenset(scope.active_workflow_run_ids | scope.pending_interaction_workflow_run_ids)
    return events, live_progress_workflow_run_ids


def with_replayed_live_state_events(
    events: list[ClientFrontendEvent],
    selected: list[ClientFrontendEvent],
    *,
    progress_replay_workflow_run_ids: frozenset[str],
) -> list[ClientFrontendEvent]:
    selected_event_ids = {
        str(event.payload.get("frontend_event_id") or "")
        for event in selected
    }
    missing_pending_interactions = [
        event
        for event in events
        if event.payload.get("frontend_event_kind") == "interaction_request"
        and str(event.payload.get("frontend_event_id") or "") not in selected_event_ids
    ]
    missing_progress = [
        event
        for event in events
        if event.payload.get("frontend_event_kind") == "progress_event"
        and str((event.payload.get("progress_event") or {}).get("workflow_run_id") or "") in progress_replay_workflow_run_ids
        and str(event.payload.get("frontend_event_id") or "") not in selected_event_ids
    ]
    if not missing_pending_interactions and not missing_progress:
        return selected
    replayed = [*missing_pending_interactions, *missing_progress, *selected]
    return sorted(replayed, key=lambda event: (str(event.payload.get("created_at") or ""), str(event.payload.get("frontend_event_id") or "")))


def pending_interaction_payloads(state_paths: StatePaths) -> list[dict[str, Any]]:
    store = InteractionRequestStore(state_paths)
    payloads: list[dict[str, Any]] = []
    for path in sorted(state_paths.pending_interactions_active_dir.glob("*.json")):
        record = store._get_active_record(path.stem)  # internal store read keeps the canonical record shape
        if record.status != "pending":
            continue
        payloads.append(dict(record.interaction_request))
    return payloads


def interaction_request_events(pending_requests: Iterable[Mapping[str, Any]]) -> Iterable[ClientFrontendEvent]:
    for request in pending_requests:
        yield ClientFrontendEvent.from_dict(
            {
                "schema_version": ClientFrontendEvent.SCHEMA_VERSION,
                "frontend_event_id": f"bridge.interaction_request.{request['interaction_request_id']}",
                "frontend_event_kind": "interaction_request",
                "mirror_event_id": request["mirror_event_id"],
                "created_at": request["created_at"],
                "interaction_request": request,
            }
        )


def progress_events(state_paths: StatePaths, scope: FrontendEventScope) -> Iterable[ClientFrontendEvent]:
    store = ProgressEventStore(state_paths)
    for workflow_dir in sorted(state_paths.events_progress_dir.iterdir()):
        if not workflow_dir.is_dir() or workflow_dir.name not in scope.visible_workflow_run_ids:
            continue
        for progress_event in store.list_progress_events(workflow_dir.name):
            payload = progress_event.to_dict()
            stable_event_id = f"bridge.progress.{payload['workflow_run_id']}.{int(payload['sequence_index']):06d}"
            yield ClientFrontendEvent.from_dict(
                {
                    "schema_version": ClientFrontendEvent.SCHEMA_VERSION,
                    "frontend_event_id": stable_event_id,
                    "frontend_event_kind": "progress_event",
                    "mirror_event_id": stable_event_id,
                    "created_at": payload.get("timestamp") or utc_iso(),
                    "progress_event": payload,
                }
            )


def mirror_events(
    state_paths: StatePaths,
    scope: FrontendEventScope,
    *,
    reset_boundary,
) -> Iterable[ClientFrontendEvent]:
    store = MirrorEventStore(state_paths)
    for path in sorted(state_paths.events_mirror_dir.glob("*.json")):
        mirror_event = store.get_mirror_event(path.stem).to_dict()
        if not scope.includes_mirror_event(mirror_event):
            continue
        created_at = str(mirror_event.get("created_at") or "") or file_mtime_iso(path)
        if not timestamp_is_after_reset_boundary(created_at, reset_boundary):
            continue
        yield ClientFrontendEvent.from_dict(
            {
                "schema_version": ClientFrontendEvent.SCHEMA_VERSION,
                "frontend_event_id": f"bridge.mirror.{mirror_event['mirror_event_id']}",
                "frontend_event_kind": "mirror_event",
                "mirror_event_id": mirror_event["mirror_event_id"],
                "created_at": created_at,
                "mirror_event": mirror_event,
            }
        )


def tool_availability_events(
    state_paths: StatePaths,
    *,
    reset_boundary,
) -> Iterable[ClientFrontendEvent]:
    for path in sorted(state_paths.events_tool_availability_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        availability = MirrorToolAvailability.from_dict(payload).to_dict()
        if not mapping_is_after_reset_boundary(availability, reset_boundary, "updated_at", "created_at"):
            continue
        yield ClientFrontendEvent.from_dict(
            {
                "schema_version": ClientFrontendEvent.SCHEMA_VERSION,
                "frontend_event_id": f"bridge.tool_availability.{availability['mirror_event_id']}",
                "frontend_event_kind": "tool_availability",
                "mirror_event_id": availability["mirror_event_id"],
                "created_at": availability["updated_at"],
                "tool_availability": availability,
            }
        )


def cursor_to_index(cursor: object) -> int:
    if cursor in (None, ""):
        return 0
    text = str(cursor)
    return int(text) if text.isdigit() else 0
