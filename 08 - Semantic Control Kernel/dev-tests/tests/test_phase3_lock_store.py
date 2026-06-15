from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from semantic_control_kernel.repository.errors import LockConflictError, StateRepositoryError, StaleLockRequiresRecoveryError
from semantic_control_kernel.repository.lock_store import LockStore
from semantic_control_kernel.repository.paths import StatePaths


TARGET = {"database_path_hash": "dbhash", "lock_scope": "database", "target_hash": "dbhash"}


def test_lock_store_acquires_non_conflicting_locks(tmp_path: Path) -> None:
    store = LockStore(StatePaths.from_state_root(tmp_path / "state"))

    first = store.acquire("database", TARGET, "wr_1", 3600, {"heartbeat_at": "2026-05-05T00:00:00Z"})
    second = store.acquire(
        "workspace",
        {"artifact_root_path_hash": "arthash", "lock_scope": "workspace", "target_hash": "arthash"},
        "wr_1",
        3600,
        {},
    )

    assert first.payload["status"] == "active"
    assert second.payload["status"] == "active"
    assert first.payload["liveness_evidence"]["database_path_hash"] == "dbhash"
    assert second.payload["liveness_evidence"]["artifact_root_path_hash"] == "arthash"


def test_lock_store_rejects_conflicting_active_locks(tmp_path: Path) -> None:
    store = LockStore(StatePaths.from_state_root(tmp_path / "state"))
    store.acquire("database", TARGET, "wr_1", 3600, {})

    with pytest.raises(LockConflictError):
        store.acquire("database", TARGET, "wr_2", 3600, {})


def test_lock_store_refreshes_heartbeat_evidence(tmp_path: Path) -> None:
    store = LockStore(StatePaths.from_state_root(tmp_path / "state"))
    lock = store.acquire("database", TARGET, "wr_1", 3600, {"heartbeat_at": "old"})

    refreshed = store.refresh(lock.payload["lock_id"], {"heartbeat_at": "new"})

    assert refreshed.payload["liveness_evidence"]["heartbeat_at"] == "new"
    assert refreshed.payload["liveness_evidence"]["database_path_hash"] == "dbhash"


def test_lock_store_marks_due_locks_expired_and_keeps_them_blocking(tmp_path: Path) -> None:
    store = LockStore(StatePaths.from_state_root(tmp_path / "state"))
    lock = store.acquire("database", TARGET, "wr_1", 1, {})
    now = datetime.now(timezone.utc) + timedelta(seconds=5)

    expired = store.expire_due_locks(now)

    assert [item.payload["lock_id"] for item in expired] == [lock.payload["lock_id"]]
    assert store.get_lock(lock.payload["lock_id"]).payload["status"] == "expired"
    with pytest.raises(StaleLockRequiresRecoveryError):
        store.acquire("database", TARGET, "wr_2", 3600, {})


def test_lock_store_rejects_locks_without_type_required_liveness_identity(tmp_path: Path) -> None:
    store = LockStore(StatePaths.from_state_root(tmp_path / "state"))

    with pytest.raises(StateRepositoryError):
        store.acquire("database", {"lock_scope": "database", "target_hash": "opaque"}, "wr_1", 3600, {})


def test_active_run_conflict_uses_workflow_run_granularity(tmp_path: Path) -> None:
    store = LockStore(StatePaths.from_state_root(tmp_path / "state"))
    evidence = {"last_progress_event_id": "pev_1", "started_at": "2026-05-05T00:00:00Z"}

    store.acquire("active_run", {"workflow_run_id": "wr_same", "target_hash": "target_a"}, "wr_same", 3600, evidence)

    with pytest.raises(LockConflictError):
        store.acquire("active_run", {"workflow_run_id": "wr_same", "target_hash": "target_b"}, "wr_same", 3600, evidence)


def test_lock_store_legacy_active_locks_without_liveness_still_block_by_target_identity(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = LockStore(paths)
    legacy_target = {"lock_scope": "database", "target_hash": "dbhash"}
    legacy_payload = {
        "acquired_at": "2026-05-05T00:00:00Z",
        "expiry_policy": {
            "expires_at": "2026-05-06T00:00:00Z",
            "heartbeat_required": True,
            "ttl_seconds": 86400,
        },
        "lock_id": "lck_legacy",
        "lock_type": "database",
        "owner_workflow_run_id": "wr_legacy",
        "schema_version": "kernel.lock_state.v1",
        "status": "active",
        "target_identity": legacy_target,
    }
    (paths.locks_active_dir / "lck_legacy.json").write_text(json.dumps(legacy_payload), encoding="utf-8")

    with pytest.raises(LockConflictError):
        store.acquire("database", TARGET, "wr_new", 3600, {})
