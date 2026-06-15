from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from semantic_control_kernel.repository._helpers import payload_from_mapping
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import (
    LockConflictError,
    LockExpiredError,
    ResumeStateNotFoundError,
    StaleLockRequiresRecoveryError,
)
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.lock_store_constants import LOCK_TYPE_TTLS, _parse_time, _validate_lock
from semantic_control_kernel.repository.lock_store_identity import conflict_key, conflict_target_key, normalize_liveness_evidence
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.terminal_transition import move_active_to_history
from semantic_control_kernel.types.state import LockState


class LockStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "locks")

    def acquire(self, lock_type, target_identity, owner_workflow_run_id, ttl_seconds, liveness_evidence) -> LockState:
        lock_type_value = str(getattr(lock_type, "value", lock_type))
        target_payload = payload_from_mapping(target_identity)
        now = datetime.now(timezone.utc)
        acquired_at = now.isoformat().replace("+00:00", "Z")
        evidence_payload = normalize_liveness_evidence(
            lock_type_value,
            target_payload,
            str(owner_workflow_run_id),
            dict(liveness_evidence),
            heartbeat_at=acquired_at,
        )
        self._raise_for_conflict(lock_type_value, target_payload, str(owner_workflow_run_id), evidence_payload)
        payload = self._lock_payload(lock_type_value, target_payload, owner_workflow_run_id, ttl_seconds, now, acquired_at, evidence_payload)
        lock = LockState.from_dict(payload)
        self._json.write_json(self._active_path(lock.payload["lock_id"]), lock.to_dict(), immutable=True, validator=_validate_lock)
        return lock

    def get_lock(self, lock_id) -> LockState:
        for path in (self._active_path(lock_id), self._history_path(lock_id)):
            if path.exists():
                return LockState.from_dict(self._json.read_json(path, validator=_validate_lock))
        raise LockExpiredError(f"Lock not found: {lock_id}")

    def list_active_locks(self, target_identity=None, lock_type=None) -> list[LockState]:
        target_key = conflict_target_key(payload_from_mapping(target_identity)) if target_identity is not None else None
        lock_type_value = str(getattr(lock_type, "value", lock_type)) if lock_type is not None else None
        locks = []
        for path in sorted(self.paths.locks_active_dir.glob("*.json")):
            lock = LockState.from_dict(self._json.read_json(path, validator=_validate_lock))
            if lock.payload["status"] not in {"active", "pending_resume", "expired"}:
                continue
            if lock_type_value is not None and lock.payload["lock_type"] != lock_type_value:
                continue
            if target_key is not None and conflict_target_key(lock.payload["target_identity"]) != target_key:
                continue
            locks.append(lock)
        return locks

    def refresh(self, lock_id, liveness_evidence) -> LockState:
        payload = self._get_active_lock(lock_id).to_dict()
        if payload["status"] == "expired":
            raise StaleLockRequiresRecoveryError(f"Expired lock requires recovery: {lock_id}")
        heartbeat_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        merged_evidence = {**payload.get("liveness_evidence", {}), **dict(liveness_evidence)}
        payload["liveness_evidence"] = normalize_liveness_evidence(
            payload["lock_type"],
            payload["target_identity"],
            payload["owner_workflow_run_id"],
            merged_evidence,
            heartbeat_at=heartbeat_at,
        )
        ttl = int(payload["expiry_policy"]["ttl_seconds"])
        payload["expiry_policy"]["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat().replace("+00:00", "Z")
        return self._write_active(payload)

    def release(self, lock_id, release_reason, receipt_ref) -> LockState:
        return self._move_terminal_lock(lock_id, status="released", reason_key="release_reason", reason=release_reason, ref_key="release_receipt_ref", ref=receipt_ref)

    def mark_failed(self, lock_id, failure_reason, receipt_ref) -> LockState:
        return self._move_terminal_lock(lock_id, status="failed", reason_key="failure_reason", reason=failure_reason, ref_key="failure_receipt_ref", ref=receipt_ref)

    def mark_pending_resume(self, lock_id, resume_state_ref) -> LockState:
        payload = self._get_active_lock(lock_id).to_dict()
        payload["status"] = "pending_resume"
        payload["liveness_evidence"] = {**payload.get("liveness_evidence", {}), "resume_state_ref": resume_state_ref}
        return self._write_active(payload)

    def expire_due_locks(self, now_utc) -> list[LockState]:
        now = now_utc if isinstance(now_utc, datetime) else _parse_time(str(now_utc))
        expired = []
        for path in sorted(self.paths.locks_active_dir.glob("*.json")):
            lock = LockState.from_dict(self._json.read_json(path, validator=_validate_lock))
            if lock.payload["status"] in {"active", "pending_resume"} and _parse_time(lock.payload["expiry_policy"]["expires_at"]) <= now:
                payload = lock.to_dict()
                payload["status"] = "expired"
                expired.append(self._write_active(payload))
        return expired

    def _raise_for_conflict(self, lock_type: str, target_identity: dict[str, Any], owner_workflow_run_id: str, liveness_evidence: dict[str, Any]) -> None:
        requested_key = conflict_key(lock_type, target_identity, owner_workflow_run_id, liveness_evidence)
        for lock in self.list_active_locks():
            existing_key = conflict_key(lock.payload["lock_type"], lock.payload["target_identity"], lock.payload["owner_workflow_run_id"], lock.payload.get("liveness_evidence", {}))
            if existing_key == requested_key:
                if lock.payload["status"] == "expired":
                    raise StaleLockRequiresRecoveryError("Expired lock still blocks mutation until recovery.")
                raise LockConflictError("Conflicting active lock exists.")

    def _move_terminal_lock(self, lock_id, *, status: str, reason_key: str, reason, ref_key: str, ref) -> LockState:
        payload = self._get_active_lock(lock_id).to_dict()
        payload[reason_key] = reason
        payload["released_at"] = utc_iso() if status == "released" else payload.get("released_at")
        payload["status"] = status
        payload["liveness_evidence"] = {**payload.get("liveness_evidence", {}), ref_key: ref}
        lock = LockState.from_dict(payload)
        self._move_to_history(lock)
        return lock

    def _lock_payload(self, lock_type: str, target_payload: dict[str, Any], owner_workflow_run_id, ttl_seconds, now: datetime, acquired_at: str, evidence_payload: dict[str, Any]) -> dict[str, Any]:
        ttl = int(ttl_seconds or LOCK_TYPE_TTLS.get(lock_type, 24 * 60 * 60))
        return {
            "acquired_at": acquired_at,
            "expiry_policy": {"expires_at": (now + timedelta(seconds=ttl)).isoformat().replace("+00:00", "Z"), "heartbeat_required": True, "ttl_seconds": ttl},
            "liveness_evidence": evidence_payload,
            "lock_id": generate_id("lock_id"),
            "lock_type": lock_type,
            "owner_workflow_run_id": owner_workflow_run_id,
            "schema_version": LockState.SCHEMA_VERSION,
            "status": "active",
            "target_identity": target_payload,
        }

    def _get_active_lock(self, lock_id: str) -> LockState:
        path = self._active_path(lock_id)
        if not path.exists():
            raise ResumeStateNotFoundError(f"Active lock not found: {lock_id}")
        return LockState.from_dict(self._json.read_json(path, validator=_validate_lock))

    def _write_active(self, payload: dict[str, Any]) -> LockState:
        lock = LockState.from_dict(payload)
        self._json.write_json(self._active_path(lock.payload["lock_id"]), lock.to_dict(), validator=_validate_lock)
        return lock

    def _move_to_history(self, lock: LockState) -> None:
        history = self._history_path(lock.payload["lock_id"])
        move_active_to_history(
            self._json,
            active_path=self._active_path(lock.payload["lock_id"]),
            history_path=history,
            payload=lock.to_dict(),
            validator=_validate_lock,
            duplicate_message=f"Lock history already exists: {lock.payload['lock_id']}",
        )
        KernelStateHardCapService(self.paths).prune_lock_history()

    def _active_path(self, lock_id: str) -> Path:
        return self.paths.locks_active_dir / f"{require_state_id('lock_id', lock_id)}.json"

    def _history_path(self, lock_id: str) -> Path:
        return self.paths.locks_history_dir / f"{require_state_id('lock_id', lock_id)}.json"
