from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_control_kernel.repository._helpers import contract_payload, parse_contract_payload, require_same_identity
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import DuplicateStateObjectError, ResumeStateNotFoundError
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.records import PendingConfirmationRecord
from semantic_control_kernel.repository.terminal_transition import move_active_to_history
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.types.receipts import ConfirmationReceipt, ConfirmationRequest


def _validate_pending_confirmation(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Pending confirmation record must be an object.")
    PendingConfirmationRecord.from_dict(payload)


class ConfirmationRequestStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "pending_confirmations")
        self._trace_store = TraceLinkStore(paths)

    def put_pending_request(self, request: ConfirmationRequest) -> None:
        request_payload = contract_payload(request, ConfirmationRequest)
        request_id = request_payload["confirmation_request_id"]
        if self._active_path(request_id).exists():
            raise DuplicateStateObjectError(f"Pending confirmation already exists: {request_id}")
        now = utc_iso()
        record = PendingConfirmationRecord(
            {
                "confirmation_request": request_payload,
                "created_at": now,
                "schema_version": PendingConfirmationRecord.SCHEMA_VERSION,
                "state_snapshot_identity": request_payload["state_snapshot_identity"],
                "status": "pending",
                "target_identity": request_payload["target_identity"],
                "updated_at": now,
                "workflow_run_id": request_payload["workflow_run_id"],
            }
        )
        active_path = self._active_path(request_id)
        self._json.write_json(active_path, record.to_dict(), immutable=True, validator=_validate_pending_confirmation)
        if self._trace_store.has_trace_context(record.workflow_run_id):
            self._trace_store.append_link_once(
                workflow_run_id=record.workflow_run_id,
                object_kind="confirmation_request",
                object_id=request_id,
                object_ref=f"{self.paths.relative_to_state_root(active_path)}#confirmation_request",
            )

    def get_pending_request(self, confirmation_request_id) -> ConfirmationRequest:
        record = self._get_active_record(confirmation_request_id)
        return parse_contract_payload(record.confirmation_request, ConfirmationRequest)

    def list_pending_for_workflow(self, workflow_run_id) -> list[ConfirmationRequest]:
        requests = []
        for path in sorted(self.paths.pending_confirmations_active_dir.glob("*.json")):
            record = PendingConfirmationRecord.from_dict(self._json.read_json(path, validator=_validate_pending_confirmation))
            if record.status != "pending":
                continue
            if record.workflow_run_id == workflow_run_id:
                requests.append(parse_contract_payload(record.confirmation_request, ConfirmationRequest))
        return requests

    def expire_pending_request(self, confirmation_request_id, reason) -> None:
        self._finalize(confirmation_request_id, "expired", expiration_reason=reason)

    def consume_pending_request(self, confirmation_request_id, confirmation_receipt_id) -> None:
        self._finalize(confirmation_request_id, "consumed", confirmation_receipt_id=confirmation_receipt_id)

    def consume_confirmation_receipt(self, receipt: ConfirmationReceipt) -> None:
        payload = contract_payload(receipt, ConfirmationReceipt)
        record = self._get_active_record(payload["confirmation_request_id"])
        require_same_identity(record.target_identity, payload["confirmed_target_identity"], "confirmation target")
        require_same_identity(record.state_snapshot_identity, payload["confirmed_state_snapshot_identity"], "confirmation snapshot")
        self.consume_pending_request(payload["confirmation_request_id"], payload["confirmation_receipt_id"])
        if self._trace_store.has_trace_context(record.workflow_run_id):
            self._trace_store.append_link_once(
                workflow_run_id=record.workflow_run_id,
                object_kind="confirmation_receipt",
                object_id=payload["confirmation_receipt_id"],
                object_ref=f"receipts/confirmations/{payload['confirmation_receipt_id']}.json",
            )

    def _finalize(self, confirmation_request_id: str, status: str, **updates: Any) -> None:
        record = self._get_active_record(confirmation_request_id)
        payload = record.to_dict()
        payload.update(updates)
        payload["status"] = status
        payload["updated_at"] = utc_iso()
        finalized = PendingConfirmationRecord(payload)
        history = self._history_path(confirmation_request_id)
        move_active_to_history(
            self._json,
            active_path=self._active_path(confirmation_request_id),
            history_path=history,
            payload=finalized.to_dict(),
            validator=_validate_pending_confirmation,
            duplicate_message=f"Pending confirmation history already exists: {confirmation_request_id}",
        )
        KernelStateHardCapService(self.paths).prune_pending_confirmation_history()

    def _get_active_record(self, confirmation_request_id: str) -> PendingConfirmationRecord:
        path = self._active_path(confirmation_request_id)
        if not path.exists():
            raise ResumeStateNotFoundError(f"Pending confirmation not found: {confirmation_request_id}")
        return PendingConfirmationRecord.from_dict(self._json.read_json(path, validator=_validate_pending_confirmation))

    def _active_path(self, confirmation_request_id: str) -> Path:
        return self.paths.pending_confirmations_active_dir / f"{require_state_id('confirmation_request_id', confirmation_request_id)}.json"

    def _history_path(self, confirmation_request_id: str) -> Path:
        return self.paths.pending_confirmations_history_dir / f"{require_state_id('confirmation_request_id', confirmation_request_id)}.json"
