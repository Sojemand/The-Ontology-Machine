from __future__ import annotations

from datetime import datetime

from semantic_control_kernel.types.state import LockState
from semantic_control_kernel.validation.contract_validation import validate_contract


LOCK_TYPE_TTLS: dict[str, int] = {
    "active_run": 24 * 60 * 60,
    "workspace": 24 * 60 * 60,
    "database": 24 * 60 * 60,
    "release_attach_activation": 2 * 60 * 60,
    "merge": 24 * 60 * 60,
    "rebuild_overwrite": 24 * 60 * 60,
}

LOCK_TYPE_REQUIRED_LIVENESS: dict[str, tuple[str, ...]] = {
    "active_run": ("workflow_run_id", "started_at", "heartbeat_at", "last_progress_event_id"),
    "workspace": ("workflow_run_id", "artifact_root_path_hash", "heartbeat_at"),
    "database": ("workflow_run_id", "database_path_hash", "heartbeat_at"),
    "release_attach_activation": ("workflow_run_id", "database_path_hash", "release_fingerprint", "heartbeat_at"),
    "merge": ("workflow_run_id", "merge_run_id", "source_database_hashes", "target_database_hash", "heartbeat_at"),
    "rebuild_overwrite": (
        "workflow_run_id",
        "target_database_hash",
        "artifact_root_path_hash",
        "overwrite_confirmation_receipt_id",
        "heartbeat_at",
    ),
}


def _validate_lock(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Lock state must be an object.")
    validate_contract(payload, expected_schema_version=LockState.SCHEMA_VERSION)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
