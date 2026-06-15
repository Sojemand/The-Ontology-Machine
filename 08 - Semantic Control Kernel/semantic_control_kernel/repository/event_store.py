from __future__ import annotations

from pathlib import Path
from typing import Mapping

from semantic_control_kernel.repository._helpers import contract_payload, parse_contract_payload
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import DuplicateStateObjectError, ResumeStateNotFoundError
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService, MIRROR_EVENT_HARD_CAP
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.records import MirrorToolAvailability
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.types.events import MirrorEvent, ProgressEvent
from semantic_control_kernel.validation.contract_validation import validate_contract


def _validate_progress(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Progress event must be an object.")
    validate_contract(payload, expected_schema_version=ProgressEvent.SCHEMA_VERSION)


def _validate_mirror(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Mirror event must be an object.")
    validate_contract(payload, expected_schema_version=MirrorEvent.SCHEMA_VERSION)


def _validate_tool_availability(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Mirror tool availability must be an object.")
    MirrorToolAvailability.from_dict(payload)


class ProgressEventStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "progress_events")
        self._trace_store = TraceLinkStore(paths)

    def append_progress_event(self, event: ProgressEvent) -> None:
        payload = contract_payload(event, ProgressEvent)
        workflow_run_id = payload["workflow_run_id"]
        sequence_index = int(payload["sequence_index"])
        event_id = payload.get("progress_event_id") or f"seq{sequence_index}"
        workflow_dir = self.paths.events_progress_dir / require_state_id('workflow_run_id', workflow_run_id)
        workflow_dir.mkdir(parents=True, exist_ok=True)
        for existing in workflow_dir.glob(f"{sequence_index:06d}_*.json"):
            raise DuplicateStateObjectError(f"Duplicate progress sequence index {sequence_index} for {workflow_run_id}")
        path = workflow_dir / f"{sequence_index:06d}_{event_id}.json"
        self._json.write_json(path, payload, immutable=True, validator=_validate_progress)
        if self._trace_store.has_trace_context(workflow_run_id):
            self._trace_store.append_link(
                workflow_run_id=workflow_run_id,
                object_kind="progress_event",
                object_id=event_id,
                object_ref=self.paths.relative_to_state_root(path),
            )
        KernelStateHardCapService(self.paths).prune_progress_workflows()

    def append_progress_event_with_next_sequence(
        self,
        payload: Mapping[str, object],
        *,
        max_attempts: int = 8,
    ) -> ProgressEvent:
        event_payload = dict(payload)
        workflow_run_id = str(event_payload.get("workflow_run_id") or "")
        if not workflow_run_id:
            raise ValueError("Progress event payload requires workflow_run_id.")
        last_duplicate: DuplicateStateObjectError | None = None
        for _attempt in range(max(1, max_attempts)):
            event_payload["sequence_index"] = self.next_sequence_index(workflow_run_id)
            event = ProgressEvent.from_dict(event_payload)
            try:
                self.append_progress_event(event)
                return event
            except DuplicateStateObjectError as exc:
                last_duplicate = exc
        if last_duplicate is not None:
            raise last_duplicate
        raise DuplicateStateObjectError(f"Could not allocate progress sequence index for {workflow_run_id}")

    def next_sequence_index(self, workflow_run_id: str) -> int:
        workflow_dir = self.paths.events_progress_dir / require_state_id('workflow_run_id', workflow_run_id)
        max_sequence = 0
        for path in workflow_dir.glob("*.json"):
            prefix = path.name.split("_", 1)[0]
            if not prefix.isdigit():
                continue
            max_sequence = max(max_sequence, int(prefix))
        return max_sequence + 1

    def list_progress_events(self, workflow_run_id) -> list[ProgressEvent]:
        workflow_dir = self.paths.events_progress_dir / require_state_id('workflow_run_id', workflow_run_id)
        events = []
        for path in sorted(workflow_dir.glob("*.json")):
            events.append(parse_contract_payload(self._json.read_json(path, validator=_validate_progress), ProgressEvent))
        return events


class MirrorEventStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "mirror_events")
        self._trace_store = TraceLinkStore(paths)
        self._hard_caps = KernelStateHardCapService(paths)

    def append_mirror_event(self, event: MirrorEvent) -> None:
        payload = contract_payload(event, MirrorEvent)
        path = self._event_path(payload["mirror_event_id"])
        self._json.write_json(path, payload, immutable=True, validator=_validate_mirror)
        workflow_run_id = payload.get("workflow_run_id")
        if isinstance(workflow_run_id, str) and workflow_run_id and self._trace_store.has_trace_context(workflow_run_id):
            self._trace_store.append_link(
                workflow_run_id=workflow_run_id,
                object_kind="mirror_event",
                object_id=payload["mirror_event_id"],
                object_ref=self.paths.relative_to_state_root(path),
            )
        self._hard_caps.prune_mirror_events()

    def get_mirror_event(self, mirror_event_id) -> MirrorEvent:
        path = self._event_path(mirror_event_id)
        if not path.exists():
            raise ResumeStateNotFoundError(f"Mirror event not found: {mirror_event_id}")
        return parse_contract_payload(self._json.read_json(path, validator=_validate_mirror), MirrorEvent)

    def put_tool_availability(self, mirror_event_id, allowed_agent_tools, expires_at) -> None:
        if not self._event_path(mirror_event_id).exists():
            raise ResumeStateNotFoundError(f"Mirror event not found: {mirror_event_id}")
        now = utc_iso()
        availability = MirrorToolAvailability(
            {
                "allowed_agent_tools": list(allowed_agent_tools),
                "created_at": now,
                "expires_at": expires_at,
                "mirror_event_id": mirror_event_id,
                "schema_version": MirrorToolAvailability.SCHEMA_VERSION,
                "status": "active",
                "updated_at": now,
            }
        )
        self._json.write_json(self._tool_path(mirror_event_id), availability.to_dict(), validator=_validate_tool_availability)

    def get_tool_availability(self, mirror_event_id) -> MirrorToolAvailability:
        path = self._tool_path(mirror_event_id)
        if not path.exists():
            raise ResumeStateNotFoundError(f"Tool availability not found: {mirror_event_id}")
        return MirrorToolAvailability.from_dict(self._json.read_json(path, validator=_validate_tool_availability))

    def mark_event_scoped_tools_expired(self, mirror_event_id, reason) -> MirrorToolAvailability:
        availability = self.get_tool_availability(mirror_event_id)
        updated = availability.with_updates(status="expired", reason=reason, updated_at=utc_iso())
        self._json.write_json(self._tool_path(mirror_event_id), updated.to_dict(), validator=_validate_tool_availability)
        return MirrorToolAvailability.from_dict(updated.to_dict())

    def _event_path(self, mirror_event_id: str) -> Path:
        return self.paths.events_mirror_dir / f"{require_state_id('mirror_event_id', mirror_event_id)}.json"

    def _tool_path(self, mirror_event_id: str) -> Path:
        return self.paths.events_tool_availability_dir / f"{require_state_id('mirror_event_id', mirror_event_id)}.json"

    def prune_mirror_events_to_hard_cap(self) -> None:
        self._hard_caps.prune_mirror_events()
