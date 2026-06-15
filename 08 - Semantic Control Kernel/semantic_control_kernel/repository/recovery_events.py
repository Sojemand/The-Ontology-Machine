from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.types.enums import RecoveryResultStatus
from semantic_control_kernel.types.recovery import (
    RECOVERY_RECEIPT_SCHEMA_VERSION,
    RecoveryEvent,
    RecoveryOption,
    Phase13RecoveryReceipt,
)
from semantic_control_kernel.validation.recovery_validation import (
    validate_recovery_event,
    validate_recovery_option,
    validate_recovery_receipt,
)


def _validate_event(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Recovery event must be an object.")
    validate_recovery_event(payload)


def _validate_options(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Recovery options file must be an object.")
    if payload.get("schema_version") != "repository.recovery_options.v1":
        raise ValueError("Recovery options file has invalid schema_version.")
    if not isinstance(payload.get("recovery_options"), list):
        raise ValueError("Recovery options file missing recovery_options.")
    for option in payload["recovery_options"]:
        validate_recovery_option(option)


def _validate_receipt(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Recovery receipt must be an object.")
    validate_recovery_receipt(payload)


class RecoveryEventStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "recovery_events")
        self._trace_store = TraceLinkStore(paths)

    def put_recovery_event(self, event: RecoveryEvent | Mapping[str, Any]) -> RecoveryEvent:
        payload = event.to_dict() if isinstance(event, RecoveryEvent) else dict(event)
        validate_recovery_event(payload)
        event_id = payload["recovery_event_id"]
        event_dir = self._event_dir(event_id)
        self._json.write_json(event_dir / "recovery_event.json", payload, validator=_validate_event)
        self._json.write_json(
            event_dir / "options.json",
            {
                "recovery_event_id": event_id,
                "recovery_options": list(payload["recovery_options"]),
                "schema_version": "repository.recovery_options.v1",
                "updated_at": utc_iso(),
            },
            validator=_validate_options,
        )
        workflow_run_id = payload.get("workflow_run_id")
        if isinstance(workflow_run_id, str) and workflow_run_id and self._trace_store.has_trace_context(workflow_run_id):
            self._trace_store.append_link_once(
                workflow_run_id=workflow_run_id,
                object_kind="recovery_event",
                object_id=event_id,
                object_ref=self.paths.relative_to_state_root(event_dir / "recovery_event.json"),
            )
            options_ref = self.paths.relative_to_state_root(event_dir / "options.json")
            for option in payload["recovery_options"]:
                if isinstance(option, Mapping) and isinstance(option.get("recovery_id"), str) and option.get("recovery_id"):
                    self._trace_store.append_link_once(
                        workflow_run_id=workflow_run_id,
                        object_kind="recovery_option",
                        object_id=str(option["recovery_id"]),
                        object_ref=f"{options_ref}#{option['recovery_id']}",
                    )
        return RecoveryEvent(payload)

    def get_recovery_event(self, recovery_event_id: str) -> RecoveryEvent:
        path = self._event_dir(recovery_event_id) / "recovery_event.json"
        if not path.exists():
            raise ResumeStateNotFoundError(f"Recovery event not found: {recovery_event_id}")
        return RecoveryEvent(self._json.read_json(path, validator=_validate_event))

    def list_options(self, recovery_event_id: str) -> tuple[RecoveryOption, ...]:
        path = self._event_dir(recovery_event_id) / "options.json"
        if not path.exists():
            raise ResumeStateNotFoundError(f"Recovery options not found: {recovery_event_id}")
        payload = self._json.read_json(path, validator=_validate_options)
        return tuple(RecoveryOption(option) for option in payload["recovery_options"])

    def get_option(self, recovery_event_id: str, recovery_id: str) -> RecoveryOption:
        for option in self.list_options(recovery_event_id):
            if option.payload["recovery_id"] == recovery_id:
                return option
        raise ResumeStateNotFoundError(f"Recovery option not found: {recovery_id}")

    def update_status(self, recovery_event_id: str, status: str, *, superseded_by: str | None = None) -> RecoveryEvent:
        event = self.get_recovery_event(recovery_event_id)
        payload = event.to_dict()
        payload["status"] = status
        payload["superseded_by"] = superseded_by
        return self.put_recovery_event(payload)

    def supersede_active_for_workflow(self, workflow_run_id: str, new_recovery_event_id: str) -> list[RecoveryEvent]:
        superseded: list[RecoveryEvent] = []
        for path in sorted(self._recovery_root().glob("*/recovery_event.json")):
            payload = self._json.read_json(path, validator=_validate_event)
            if (
                payload.get("workflow_run_id") == workflow_run_id
                and payload.get("recovery_event_id") != new_recovery_event_id
                and payload.get("status") == "active"
            ):
                payload["status"] = "superseded"
                payload["superseded_by"] = new_recovery_event_id
                superseded.append(self.put_recovery_event(payload))
        return superseded

    def append_recovery_receipt(
        self,
        *,
        recovery_event: RecoveryEvent | Mapping[str, Any],
        recovery_id: str,
        result_status: str,
        selected_recovery_option: Mapping[str, Any] | None = None,
        target_identity_after: Mapping[str, Any] | None = None,
        written_refs: Sequence[Mapping[str, Any]] = (),
        mutated_refs: Sequence[Mapping[str, Any]] = (),
        user_confirmation_refs: Sequence[Mapping[str, Any]] = (),
        support_bundle_ref: Mapping[str, Any] | None = None,
        recovery_receipt_id: str | None = None,
    ) -> Phase13RecoveryReceipt:
        event_payload = recovery_event.to_dict() if isinstance(recovery_event, RecoveryEvent) else dict(recovery_event)
        validate_recovery_event(event_payload)
        receipt_id = recovery_receipt_id or generate_id("recovery_receipt_id")
        payload = {
            "created_at": utc_iso(),
            "mirror_event_id": event_payload["mirror_event_id"],
            "mutated_refs": [dict(ref) for ref in mutated_refs],
            "recovery_event_id": event_payload["recovery_event_id"],
            "recovery_id": recovery_id,
            "recovery_receipt_id": receipt_id,
            "recovery_state": event_payload["recovery_state"],
            "result_status": result_status,
            "schema_version": RECOVERY_RECEIPT_SCHEMA_VERSION,
            "selected_recovery_option": dict(selected_recovery_option or {}),
            "state_snapshot_identity": dict(event_payload["state_snapshot_identity"]),
            "support_bundle_ref": dict(support_bundle_ref or event_payload.get("support_bundle_ref") or {}),
            "target_identity_after": dict(target_identity_after or event_payload["target_identity"]),
            "target_identity_before": dict(event_payload["target_identity"]),
            "user_confirmation_refs": [dict(ref) for ref in user_confirmation_refs],
            "workflow_run_id": event_payload["workflow_run_id"],
            "written_refs": [dict(ref) for ref in written_refs],
        }
        validate_recovery_receipt(payload)
        receipt_path = self.paths.receipts_recoveries_dir / f"{receipt_id}.json"
        self._json.write_json(receipt_path, payload, immutable=True, validator=_validate_receipt)
        workflow_run_id = payload.get("workflow_run_id")
        if isinstance(workflow_run_id, str) and workflow_run_id and self._trace_store.has_trace_context(workflow_run_id):
            self._trace_store.append_link_once(
                workflow_run_id=workflow_run_id,
                object_kind="recovery_receipt",
                object_id=receipt_id,
                object_ref=self.paths.relative_to_state_root(receipt_path),
            )
        return Phase13RecoveryReceipt(payload)

    def append_rejection_receipt(
        self,
        recovery_event_id: str,
        *,
        recovery_id: str,
        reason: str,
    ) -> Phase13RecoveryReceipt:
        event = self.get_recovery_event(recovery_event_id)
        return self.append_recovery_receipt(
            recovery_event=event,
            recovery_id=recovery_id,
            result_status=RecoveryResultStatus.REJECTED.value,
            selected_recovery_option={"rejection_reason": reason},
        )

    def _recovery_root(self) -> Path:
        root = self.paths.events_recovery_dir
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _event_dir(self, recovery_event_id: str) -> Path:
        return self._recovery_root() / require_state_id("recovery_event_id", recovery_event_id)
