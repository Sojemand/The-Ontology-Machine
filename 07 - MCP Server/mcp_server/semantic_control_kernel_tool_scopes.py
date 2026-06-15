from __future__ import annotations


HOST_ONLY_CLIENT_BRIDGE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "kernel_list_client_frontend_events": (
        "schema_version",
        "host_surface_identity",
        "client_instance_id",
        "client_request_id",
    ),
    "kernel_submit_user_interaction_response": (
        "schema_version",
        "interaction_request_id",
        "response",
        "target_identity",
        "state_snapshot_identity",
        "host_surface_identity",
        "client_request_id",
    ),
    "kernel_cancel_user_interaction": (
        "schema_version",
        "interaction_request_id",
        "response_status",
        "target_identity",
        "state_snapshot_identity",
        "host_surface_identity",
        "client_request_id",
    ),
    "kernel_list_event_scoped_tool_definitions": (
        "schema_version",
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "host_surface_identity",
        "client_request_id",
    ),
}

FORWARDABLE_CLIENT_CONTEXT_FIELDS: frozenset[str] = frozenset(
    {
        "client_request_id",
        "conversation_ref",
        "turn_ref",
    }
)

EVENT_SCOPED_TOOL_SCOPE_FIELDS: dict[str, tuple[str, ...]] = {
    "kernel_apply_recovery_option": (
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
        "recovery_id",
        "tool_call_nonce",
    ),
    "kernel_open_recovery_dialog": (
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
        "recovery_id",
        "tool_call_nonce",
    ),
    "kernel_retry_recoverable_workflow": (
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
        "recovery_id",
        "workflow_run_id",
        "tool_call_nonce",
    ),
    "kernel_resolve_stale_lock": (
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
        "recovery_id",
        "lock_id",
        "tool_call_nonce",
    ),
    "kernel_rebind_database_artifact_tree": (
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
        "recovery_id",
        "binding_recovery_id",
        "tool_call_nonce",
    ),
    "kernel_discard_or_archive_staged_work": (
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
        "recovery_id",
        "staged_work_ref",
        "tool_call_nonce",
    ),
    "kernel_reconcile_partial_pipeline_run": (
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
        "recovery_id",
        "partial_run_ref",
        "tool_call_nonce",
    ),
    "kernel_open_support_bundle": (
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
        "recovery_id",
        "support_bundle_id",
        "tool_call_nonce",
    ),
}

KERNEL_INTERNAL_SCOPE_FIELDS: tuple[str, ...] = (
    "kernel_internal_call_id",
    "workflow_run_id",
    "state_snapshot_id",
    "tool_name",
    "arguments",
)

KERNEL_CONTINUATION_SCOPE_FIELDS: tuple[str, ...] = ()
