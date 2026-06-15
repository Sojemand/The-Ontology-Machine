from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from semantic_control_kernel.repository._helpers import contract_payload, parse_contract_payload, require_same_identity
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import DuplicateStateObjectError, ResumeStateNotFoundError, TargetIdentityMismatchError
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.records import PendingInteractionRecord
from semantic_control_kernel.repository.terminal_transition import move_active_to_history
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.types.events import UserInteractionRequest, UserInteractionResponse

STALE_RESPONSE_REFS_HARD_CAP = 20


def _validate_pending_interaction(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Pending interaction record must be an object.")
    PendingInteractionRecord.from_dict(payload)


class InteractionRequestStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "pending_interactions")
        self._trace_store = TraceLinkStore(paths)

    def put_pending_interaction(self, request: UserInteractionRequest) -> None:
        request_payload = contract_payload(request, UserInteractionRequest)
        request_id = request_payload["interaction_request_id"]
        if self._active_path(request_id).exists():
            raise DuplicateStateObjectError(f"Pending interaction already exists: {request_id}")
        now = utc_iso()
        record = PendingInteractionRecord(
            {
                "created_at": now,
                "interaction_request": request_payload,
                "schema_version": PendingInteractionRecord.SCHEMA_VERSION,
                "state_snapshot_identity": request_payload["state_snapshot_identity"],
                "status": "pending",
                "target_identity": request_payload["target_identity"],
                "updated_at": now,
                "workflow_run_id": request_payload["workflow_run_id"],
            }
        )
        active_path = self._active_path(request_id)
        self._json.write_json(active_path, record.to_dict(), immutable=True, validator=_validate_pending_interaction)
        if self._trace_store.has_trace_context(record.workflow_run_id):
            self._trace_store.append_link_once(
                workflow_run_id=record.workflow_run_id,
                object_kind="interaction_request",
                object_id=request_id,
                object_ref=f"{self.paths.relative_to_state_root(active_path)}#interaction_request",
            )

    def get_pending_interaction(self, interaction_request_id) -> UserInteractionRequest:
        record = self._get_active_record(interaction_request_id)
        return parse_contract_payload(record.interaction_request, UserInteractionRequest)

    def list_pending_interactions_for_workflow(self, workflow_run_id) -> list[UserInteractionRequest]:
        requests = []
        for path in sorted(self.paths.pending_interactions_active_dir.glob("*.json")):
            record = PendingInteractionRecord.from_dict(self._json.read_json(path, validator=_validate_pending_interaction))
            if record.workflow_run_id == workflow_run_id and record.status == "pending":
                requests.append(parse_contract_payload(record.interaction_request, UserInteractionRequest))
        return requests

    def list_records_for_workflow(self, workflow_run_id, *, include_active: bool = True, include_history: bool = True) -> list[PendingInteractionRecord]:
        records: list[PendingInteractionRecord] = []
        if include_active:
            for path in sorted(self.paths.pending_interactions_active_dir.glob("*.json")):
                record = PendingInteractionRecord.from_dict(self._json.read_json(path, validator=_validate_pending_interaction))
                if record.status != "pending":
                    continue
                if record.workflow_run_id == workflow_run_id:
                    records.append(record)
        if include_history:
            for path in sorted(self.paths.pending_interactions_history_dir.glob("*.json")):
                record = PendingInteractionRecord.from_dict(self._json.read_json(path, validator=_validate_pending_interaction))
                if record.workflow_run_id == workflow_run_id:
                    records.append(record)
        return records

    def submit_interaction(self, interaction_request_id, interaction_response_id, *, interaction_response: dict[str, Any] | None = None) -> None:
        updates: dict[str, Any] = {"interaction_response_id": interaction_response_id}
        if interaction_response is not None:
            updates["interaction_response"] = dict(interaction_response)
        self._finalize(interaction_request_id, "submitted", **updates)

    def submit_interaction_response(self, response: UserInteractionResponse, now_utc: datetime | None = None) -> None:
        payload = contract_payload(response, UserInteractionResponse)
        record = self._get_active_record(payload["interaction_request_id"])
        if record.workflow_run_id != payload.get("workflow_run_id", record.workflow_run_id):
            raise TargetIdentityMismatchError("interaction workflow identity mismatch")
        require_same_identity(record.target_identity, payload["target_identity"], "interaction target")
        require_same_identity(record.state_snapshot_identity, payload["state_snapshot_identity"], "interaction snapshot")
        self._reject_expired(record, now_utc=now_utc)
        self.submit_interaction(
            payload["interaction_request_id"],
            payload["interaction_response_id"],
            interaction_response=payload,
        )
        if self._trace_store.has_trace_context(record.workflow_run_id):
            self._trace_store.append_link_once(
                workflow_run_id=record.workflow_run_id,
                object_kind="interaction_response",
                object_id=payload["interaction_response_id"],
                object_ref=f"{self.paths.relative_to_state_root(self._history_path(payload['interaction_request_id']))}#interaction_response_id",
            )

    def cancel_interaction(self, interaction_request_id, reason) -> None:
        self._finalize(interaction_request_id, "cancelled", reason=reason)

    def close_interaction(self, interaction_request_id, reason) -> None:
        self._finalize(interaction_request_id, "closed", reason=reason)

    def expire_interaction(self, interaction_request_id, reason) -> None:
        self._finalize(interaction_request_id, "expired", reason=reason)

    def supersede_interaction(self, interaction_request_id, superseding_workflow_run_id=None) -> None:
        updates = {}
        if superseding_workflow_run_id is not None:
            updates["superseding_workflow_run_id"] = superseding_workflow_run_id
        self._finalize(interaction_request_id, "superseded", **updates)

    def reject_stale_interaction(self, interaction_request_id, reason) -> None:
        self._finalize(interaction_request_id, "rejected_stale", reason=reason)

    def record_stale_response_ref(self, interaction_request_id: str, response_ref: dict[str, Any]) -> None:
        record = self._get_record_anywhere(interaction_request_id)
        refs = list(record.payload.get("stale_response_refs", []))
        refs.append(response_ref)
        if len(refs) > STALE_RESPONSE_REFS_HARD_CAP:
            refs = refs[-STALE_RESPONSE_REFS_HARD_CAP:]
        payload = record.to_dict()
        payload["stale_response_refs"] = refs
        path = self._history_path(interaction_request_id) if record.status != "pending" else self._active_path(interaction_request_id)
        self._json.write_json(path, PendingInteractionRecord(payload).to_dict(), validator=_validate_pending_interaction)

    def _finalize(self, interaction_request_id: str, status: str, **updates: Any) -> None:
        record = self._get_active_record(interaction_request_id)
        payload = record.to_dict()
        payload.update(updates)
        payload["status"] = status
        payload["updated_at"] = utc_iso()
        finalized = PendingInteractionRecord(payload)
        move_active_to_history(
            self._json,
            active_path=self._active_path(interaction_request_id),
            history_path=self._history_path(interaction_request_id),
            payload=finalized.to_dict(),
            validator=_validate_pending_interaction,
            duplicate_message=f"Pending interaction history already exists: {interaction_request_id}",
        )
        KernelStateHardCapService(self.paths).prune_pending_interaction_history()

    def _reject_expired(self, record: PendingInteractionRecord, now_utc: datetime | None) -> None:
        expiration_policy = record.interaction_request.get("expiration_policy", {})
        expires_at = expiration_policy.get("expires_at") if isinstance(expiration_policy, dict) else None
        if not expires_at:
            return
        now = now_utc or datetime.now(timezone.utc)
        if now >= datetime.fromisoformat(expires_at.replace("Z", "+00:00")):
            raise TargetIdentityMismatchError("interaction response is expired")

    def _get_active_record(self, interaction_request_id: str) -> PendingInteractionRecord:
        path = self._active_path(interaction_request_id)
        if not path.exists():
            raise ResumeStateNotFoundError(f"Pending interaction not found: {interaction_request_id}")
        return PendingInteractionRecord.from_dict(self._json.read_json(path, validator=_validate_pending_interaction))

    def _get_record_anywhere(self, interaction_request_id: str) -> PendingInteractionRecord:
        for path in (self._active_path(interaction_request_id), self._history_path(interaction_request_id)):
            if path.exists():
                return PendingInteractionRecord.from_dict(self._json.read_json(path, validator=_validate_pending_interaction))
        raise ResumeStateNotFoundError(f"Interaction not found: {interaction_request_id}")

    def _active_path(self, interaction_request_id: str) -> Path:
        return self.paths.pending_interactions_active_dir / f"{require_state_id('interaction_request_id', interaction_request_id)}.json"

    def _history_path(self, interaction_request_id: str) -> Path:
        return self.paths.pending_interactions_history_dir / f"{require_state_id('interaction_request_id', interaction_request_id)}.json"
