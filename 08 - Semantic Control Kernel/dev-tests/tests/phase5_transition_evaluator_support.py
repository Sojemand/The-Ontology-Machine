from __future__ import annotations

from semantic_control_kernel.domain.state_machine.models import TransitionRule
from semantic_control_kernel.types.state import ActiveDatabaseState

TARGET_IDENTITY = {
    "schema_version": "state.target_identity.v1",
    "database_path_hash": "dbhash",
    "artifact_root_path_hash": "arthash",
    "lock_scope": "database",
    "target_hash": "dbhash",
    "created_from": "test",
}


def state_for_rule(rule: TransitionRule, *, invalid: bool = False, active_lock_status: str | None = None) -> ActiveDatabaseState:
    semantic_state = semantic_state_for(rule)
    emptiness = emptiness_for(rule)
    artifact_exists = "no_active_artifact_tree_required" not in rule.required_state
    database_exists = True
    if invalid:
        semantic_state = "unknown"
        emptiness = "unknown"
        artifact_exists = "no_active_artifact_tree_required" in rule.required_state
        database_exists = False
    active_lock_refs = []
    if active_lock_status:
        active_lock_refs.append({"lock_id": "lock_1", "lock_type": "active_run", "status": active_lock_status})
    payload = {
        "schema_version": ActiveDatabaseState.SCHEMA_VERSION,
        "state_snapshot_id": "state_test",
        "artifact_tree": {"exists": artifact_exists, "target_identity": TARGET_IDENTITY},
        "active_database": {"database_exists": database_exists, "target_identity": TARGET_IDENTITY},
        "database_emptiness": emptiness,
        "semantic_release_state": semantic_state,
        "blocking_reasons": [],
        "active_lock_refs": active_lock_refs,
        "evidence_refs": [],
    }
    return ActiveDatabaseState.from_dict(payload)


def semantic_state_for(rule: TransitionRule) -> str:
    for candidate in (
        "semantic_release_active",
        "semantic_release_complete_not_active",
        "semantic_release_incomplete",
        "no_semantic_release",
    ):
        if candidate in rule.required_state:
            return candidate
    return "semantic_release_active"


def emptiness_for(rule: TransitionRule) -> str:
    if "database_empty_required" in rule.required_state:
        return "empty"
    if "database_filled_required" in rule.required_state:
        return "filled"
    return "filled"
