from __future__ import annotations

from pathlib import Path

import pytest

from semantic_control_kernel import mcp_contract
from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.domain.recovery.stale_lock import StaleLockRecoveryService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.lock_store import LockStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import LockType, MirrorEventType, MirrorSeverity, RecoveryStateClass
from semantic_control_kernel.types.recovery import RECOVERY_EVENT_SCHEMA_VERSION


TARGET = {
    "database_path_hash": "dbhash_stale_lock",
    "lock_scope": "database",
    "target_hash": "target_stale_lock",
}
SNAPSHOT = {"state_snapshot_id": "ss_stale_lock"}
OTHER_TARGET = {
    "database_path_hash": "dbhash_other_lock",
    "lock_scope": "database",
    "target_hash": "target_other_lock",
}


def _event(paths: StatePaths):
    recovery_store = RecoveryEventStore(paths)
    mirror_store = MirrorEventStore(paths)
    expires_at = RecoveryPolicy().expires_at(RecoveryStateClass.STALE_LOCK.value)
    options = RecoveryOptionService().create_options(
        recovery_event_id="rev_stale_lock",
        recovery_state=RecoveryStateClass.STALE_LOCK.value,
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        expires_at=expires_at,
        safe_tools=("kernel_resolve_stale_lock",),
    )
    mirror = KernelMirrorEventService(mirror_store).create_mirror_event(
        event_type=MirrorEventType.RECOVERY_STATE.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        user_visible_summary="Stale lock.",
        current_state_summary="Lock recovery.",
        recovery_options=[option.to_dict() for option in options],
        allowed_agent_tools=("kernel_resolve_stale_lock",),
        tool_availability_expires_at=expires_at,
    )
    event = recovery_store.put_recovery_event(
        {
            "allowed_agent_tools": ["kernel_resolve_stale_lock"],
            "blocked_functions": ["manual_pipeline_run"],
            "cause_code": "stale_lock",
            "created_at": utc_iso(),
            "detected_by": "LockStore",
            "expires_at": expires_at,
            "failed_kernel_step": "lock_step",
            "mirror_event_id": mirror.payload["mirror_event_id"],
            "recovery_event_id": "rev_stale_lock",
            "recovery_options": [option.to_dict() for option in options],
            "recovery_state": "stale_lock",
            "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
            "state_snapshot_identity": SNAPSHOT,
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": TARGET,
            "user_visible_cause": "A lock may be stale.",
            "workflow_run_id": "wr_stale_lock",
            "workflow_tool": "manual_pipeline_run",
        }
    )
    return recovery_store, event, options[0]


@pytest.mark.parametrize(
    ("evidence", "expected_result", "expected_status"),
    [
        ({"owner_live": True}, "rejected", "active"),
        ({"owner_dead": True, "partial_mutation_risk": False}, "applied", "released"),
        ({"owner_dead": True, "safe_resume_point": True}, "applied", "pending_resume"),
        ({"owner_dead": True, "partial_mutation_risk": True}, "applied", "failed"),
        ({"owner_dead": True, "partial_mutation_risk": True, "safe_resume_point": True}, "applied", "failed"),
        ({}, "rejected", "active"),
    ],
)
def test_stale_lock_recovery_requires_liveness_proof(tmp_path: Path, evidence, expected_result: str, expected_status: str) -> None:
    paths = StatePaths.from_state_root(tmp_path / expected_status / "state")
    lock_store = LockStore(paths)
    recovery_store, event, option = _event(paths)
    lock = lock_store.acquire(LockType.DATABASE, TARGET, "wr_stale_lock", 1, evidence)

    result = StaleLockRecoveryService(lock_store, recovery_store).resolve_lock(event.payload, option.payload["recovery_id"], lock.payload["lock_id"])

    assert result["result_status"] == expected_result
    assert result["lock_status_after"] == expected_status
    assert result["receipt"].payload["recovery_event_id"] == event.payload["recovery_event_id"]
    assert result["receipt"].payload["result_status"] in {"applied", "rejected"}


def test_stale_lock_recovery_rejects_lock_for_different_target_identity(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    lock_store = LockStore(paths)
    recovery_store, event, option = _event(paths)
    lock = lock_store.acquire(LockType.DATABASE, OTHER_TARGET, "wr_other_lock", 1, {"owner_dead": True})

    result = StaleLockRecoveryService(lock_store, recovery_store).resolve_lock(
        event.payload,
        option.payload["recovery_id"],
        lock.payload["lock_id"],
    )

    assert result["result_status"] == "rejected"
    assert result["lock_status_after"] == "active"
    assert lock_store.get_lock(lock.payload["lock_id"]).payload["status"] == "active"
    assert result["receipt"].payload["selected_recovery_option"]["rejection_reason"] == "target_identity_changed"


def test_event_scoped_mcp_stale_lock_tool_uses_live_recovery_service(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    lock_store = LockStore(paths)
    _recovery_store, event, option = _event(paths)
    lock = lock_store.acquire(LockType.DATABASE, TARGET, "wr_stale_lock", 1, {"owner_dead": True})
    monkeypatch.setenv("VISION_KERNEL_STATE_ROOT", str(paths.state_root))

    response = mcp_contract.call_mcp_tool(
        {
            "schema_version": "semantic_control_kernel.mcp_request.v1",
            "transport": "mcp_server",
            "tool_name": "kernel_resolve_stale_lock",
            "visibility": "event_scoped",
            "model_arguments": {},
            "client_context": {
                "host_surface_identity": "test_host",
                "client_request_id": "req_stale_lock",
            },
            "event_scope": {
                "mirror_event_id": event.payload["mirror_event_id"],
                "recovery_event_id": event.payload["recovery_event_id"],
                "state_snapshot_id": SNAPSHOT["state_snapshot_id"],
                "client_request_id": "req_stale_lock",
                "recovery_id": option.payload["recovery_id"],
                "lock_id": lock.payload["lock_id"],
                "tool_call_nonce": "nonce_stale_lock",
            },
        }
    )

    assert response["status"] == "completed"
    assert response["lock_status_after"] == "released"
    assert lock_store.get_lock(lock.payload["lock_id"]).payload["status"] == "released"
