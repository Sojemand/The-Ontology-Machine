from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.records import MirrorToolAvailability
from semantic_control_kernel.repository.run_store import WorkflowRunStore


@dataclass(frozen=True)
class FrontendEventScope:
    active_workflow_run_ids: frozenset[str]
    pending_interaction_workflow_run_ids: frozenset[str]
    recent_terminal_workflow_run_ids: frozenset[str]
    pending_interaction_mirror_event_ids: frozenset[str]
    tool_availability_mirror_event_ids: frozenset[str]

    @property
    def visible_workflow_run_ids(self) -> frozenset[str]:
        return frozenset(
            self.active_workflow_run_ids
            | self.pending_interaction_workflow_run_ids
            | self.recent_terminal_workflow_run_ids
        )

    def includes_mirror_event(self, mirror_event: Mapping[str, Any]) -> bool:
        mirror_event_id = str(mirror_event.get("mirror_event_id") or "")
        workflow_run_id = str(mirror_event.get("workflow_run_id") or "")
        if mirror_event_id in self.pending_interaction_mirror_event_ids or mirror_event_id in self.tool_availability_mirror_event_ids:
            return True
        if str(mirror_event.get("kernel_dialog_state") or "") == "open":
            return False
        return workflow_run_id in self.visible_workflow_run_ids


def frontend_event_scope(
    state_paths: StatePaths,
    pending_requests: Iterable[Mapping[str, Any]],
    *,
    reset_boundary: datetime | None,
) -> FrontendEventScope:
    active_workflow_run_ids = frozenset(
        str(record.workflow_run_id)
        for record in WorkflowRunStore(state_paths).list_active_runs()
    )
    pending_requests_list = list(pending_requests)
    pending_interaction_workflow_run_ids = frozenset(
        str(request.get("workflow_run_id") or "")
        for request in pending_requests_list
        if str(request.get("workflow_run_id") or "")
    )
    pending_interaction_mirror_event_ids = frozenset(
        str(request.get("mirror_event_id") or "")
        for request in pending_requests_list
        if str(request.get("mirror_event_id") or "")
    )
    return FrontendEventScope(
        active_workflow_run_ids=active_workflow_run_ids,
        pending_interaction_workflow_run_ids=pending_interaction_workflow_run_ids,
        recent_terminal_workflow_run_ids=recent_terminal_workflow_run_ids(
            state_paths,
            reset_boundary=reset_boundary,
        ),
        pending_interaction_mirror_event_ids=pending_interaction_mirror_event_ids,
        tool_availability_mirror_event_ids=tool_availability_mirror_event_ids(
            state_paths,
            reset_boundary=reset_boundary,
        ),
    )


def recent_terminal_workflow_run_ids(
    state_paths: StatePaths,
    *,
    max_age_seconds: int = 900,
    reset_boundary: datetime | None = None,
) -> frozenset[str]:
    store = WorkflowRunStore(state_paths)
    now = datetime.now(timezone.utc)
    visible: set[str] = set()
    for path in sorted(state_paths.workflow_runs_history_dir.glob("*.json")):
        try:
            record = store.get_run(path.stem)
        except ResumeStateNotFoundError:
            continue
        if str(record.status) not in {"completed", "failed", "cancelled"}:
            continue
        updated_at = iso_datetime(record.updated_at)
        if updated_at is None or not datetime_is_after_reset_boundary(updated_at, reset_boundary):
            continue
        age_seconds = (now - updated_at).total_seconds()
        if age_seconds < 0 or age_seconds <= max_age_seconds:
            visible.add(str(record.workflow_run_id))
    return frozenset(visible)


def tool_availability_mirror_event_ids(
    state_paths: StatePaths,
    *,
    reset_boundary: datetime | None,
) -> frozenset[str]:
    visible: set[str] = set()
    for path in sorted(state_paths.events_tool_availability_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        availability = MirrorToolAvailability.from_dict(payload).to_dict()
        if mapping_is_after_reset_boundary(availability, reset_boundary, "updated_at", "created_at"):
            visible.add(str(availability["mirror_event_id"]))
    return frozenset(visible)


def latest_reset_created_at(state_paths: StatePaths) -> datetime | None:
    latest: datetime | None = None
    for path in sorted(state_paths.archive_resets_dir.glob("*/reset_manifest.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        created_at = iso_datetime(payload.get("created_at"))
        if created_at is not None and (latest is None or created_at > latest):
            latest = created_at
    return latest


def mapping_is_after_reset_boundary(
    payload: Mapping[str, Any],
    reset_boundary: datetime | None,
    *timestamp_fields: str,
) -> bool:
    if reset_boundary is None:
        return True
    return any(
        timestamp_is_after_reset_boundary(payload.get(field_name), reset_boundary)
        for field_name in timestamp_fields
    )


def timestamp_is_after_reset_boundary(value: object, reset_boundary: datetime | None) -> bool:
    if reset_boundary is None:
        return True
    return datetime_is_after_reset_boundary(iso_datetime(value), reset_boundary)


def datetime_is_after_reset_boundary(value: datetime | None, reset_boundary: datetime | None) -> bool:
    if reset_boundary is None:
        return True
    return value is not None and value > reset_boundary


def is_expired(value: object) -> bool:
    expires_at = iso_datetime(value)
    if expires_at is None:
        return True
    return expires_at <= datetime.now(timezone.utc)


def state_snapshot_id(payload: object) -> str:
    if isinstance(payload, Mapping):
        value = payload.get("state_snapshot_id")
        return str(value or "")
    return ""


def file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")


def iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
