from __future__ import annotations


TARGET_IDENTITY_ALLOWED_FIELDS = frozenset(
    {
        "schema_version",
        "database_path_hash",
        "artifact_root_path_hash",
        "lock_scope",
        "target_hash",
        "created_from",
        "database_id",
        "release_fingerprint",
        "semantic_release_identity_hash",
        "taxonomy_fingerprint",
        "projection_set_hash",
        "pipeline_batch_id",
        "source_database_set_hash",
        "workflow_run_id",
        "parent_path_hash",
        "input_path_hash",
    }
)
STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS = frozenset({"schema_version", "state_snapshot_id"})
INTERACTION_EXPIRATION_POLICY_ALLOWED_FIELDS = frozenset(
    {"policy_id", "ttl_seconds", "expires_at", "recovery_state"}
)
LOCK_EXPIRY_POLICY_ALLOWED_FIELDS = frozenset({"expires_at", "heartbeat_required", "ttl_seconds"})

CLOSED_MAPPING_FIELD_RULES: dict[str, dict[str, frozenset[str]]] = {
    "kernel.confirmation_request.v1": {
        "expiration_policy": INTERACTION_EXPIRATION_POLICY_ALLOWED_FIELDS,
        "state_snapshot_identity": STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
        "target_identity": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.confirmation_receipt.v1": {
        "confirmed_state_snapshot_identity": STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
        "confirmed_target_identity": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.user_interaction_request.v1": {
        "expiration_policy": INTERACTION_EXPIRATION_POLICY_ALLOWED_FIELDS,
        "state_snapshot_identity": STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
        "target_identity": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.user_interaction_response.v1": {
        "state_snapshot_identity": STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
        "target_identity": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.database_merge_reconciliation_receipt.v1": {
        "state_snapshot_identity": STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
        "target_identity": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.operation_receipt.v1": {
        "target_identity_after": TARGET_IDENTITY_ALLOWED_FIELDS,
        "target_identity_before": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.lock_state.v1": {
        "expiry_policy": LOCK_EXPIRY_POLICY_ALLOWED_FIELDS,
        "target_identity": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.workflow_resume_state.v1": {
        "state_snapshot_identity": STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.resume_option.v1": {
        "target_identity": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.recovery_option.v1": {
        "state_snapshot_identity": STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
        "target_identity": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
    "kernel.recovery_receipt.v1": {
        "state_snapshot_identity": STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
        "target_identity_after": TARGET_IDENTITY_ALLOWED_FIELDS,
        "target_identity_before": TARGET_IDENTITY_ALLOWED_FIELDS,
    },
}
