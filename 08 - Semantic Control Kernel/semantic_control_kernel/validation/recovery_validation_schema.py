from __future__ import annotations


RECOVERY_EVENT_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "recovery_event_id",
    "recovery_state",
    "workflow_run_id",
    "workflow_tool",
    "failed_kernel_step",
    "detected_by",
    "target_identity",
    "state_snapshot_identity",
    "cause_code",
    "user_visible_cause",
    "blocked_functions",
    "recovery_options",
    "allowed_agent_tools",
    "mirror_event_id",
    "support_bundle_ref",
    "status",
    "created_at",
    "expires_at",
    "superseded_by",
)

RECOVERY_OPTION_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "recovery_id",
    "recovery_event_id",
    "label",
    "description",
    "owner",
    "recovery_action_type",
    "effect",
    "risk_class",
    "target_identity",
    "state_snapshot_identity",
    "agent_tool",
    "kernel_dialog_action",
    "starts_new_workflow",
    "continuation_workflow_tool",
    "requires_confirmation",
    "expires_at",
)

RECOVERY_RECEIPT_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "recovery_receipt_id",
    "recovery_id",
    "recovery_event_id",
    "mirror_event_id",
    "workflow_run_id",
    "recovery_state",
    "selected_recovery_option",
    "target_identity_before",
    "target_identity_after",
    "state_snapshot_identity",
    "result_status",
    "written_refs",
    "mutated_refs",
    "user_confirmation_refs",
    "support_bundle_ref",
    "created_at",
)

SUPPORT_BUNDLE_REF_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "support_bundle_id",
    "support_bundle_path",
    "created_at",
    "category",
    "workflow_run_id",
    "recovery_event_id",
    "safe_summary",
    "included_refs",
    "redaction_profile",
)

RECOVERY_EVENT_STATUSES: tuple[str, ...] = (
    "active",
    "resolved",
    "cancelled",
    "expired",
    "superseded",
    "support_only",
)

_RECOVERY_TOOL_INPUT_BASE = ("schema_version", "mirror_event_id", "recovery_event_id", "recovery_id")
_RECOVERY_TOOL_INPUT_EXTRA: dict[str, tuple[str, ...]] = {
    "kernel_apply_recovery_option": (),
    "kernel_open_recovery_dialog": (),
    "kernel_retry_recoverable_workflow": ("workflow_run_id",),
    "kernel_resolve_stale_lock": ("lock_id",),
    "kernel_rebind_database_artifact_tree": ("binding_recovery_id",),
    "kernel_discard_or_archive_staged_work": ("staged_work_ref",),
    "kernel_reconcile_partial_pipeline_run": ("partial_run_ref",),
    "kernel_open_support_bundle": ("support_bundle_id",),
}

RECOVERY_TOOL_INPUT_FIELDS: dict[str, tuple[str, ...]] = {
    tool_name: _RECOVERY_TOOL_INPUT_BASE + extra_fields + ("tool_call_nonce",)
    for tool_name, extra_fields in _RECOVERY_TOOL_INPUT_EXTRA.items()
}

_RECOVERY_TOOL_OUTPUT_BASE = ("schema_version", "result_status")
_RECOVERY_TOOL_OUTPUT_EXTRA: dict[str, tuple[str, ...]] = {
    "kernel_apply_recovery_option": (
        "recovery_receipt_id",
        "next_kernel_event",
        "opened_dialog_ref",
        "support_bundle_ref",
    ),
    "kernel_open_recovery_dialog": ("recovery_receipt_id", "dialog_request_ref", "kernel_dialog_state"),
    "kernel_retry_recoverable_workflow": (
        "new_or_resumed_workflow_run_id",
        "recovery_receipt_id",
        "progress_event_ref",
        "support_bundle_ref",
    ),
    "kernel_resolve_stale_lock": ("lock_id", "lock_status_after", "recovery_receipt_id", "support_bundle_ref"),
    "kernel_rebind_database_artifact_tree": (
        "binding_receipt_id",
        "recovery_receipt_id",
        "database_artifact_binding_ref",
        "support_bundle_ref",
    ),
    "kernel_discard_or_archive_staged_work": (
        "archive_ref",
        "discard_receipt_id",
        "recovery_receipt_id",
        "support_bundle_ref",
    ),
    "kernel_reconcile_partial_pipeline_run": (
        "reconciliation_receipt_id",
        "finalized_manifest_ref",
        "quarantine_ref",
        "new_recovery_event_ref",
        "support_bundle_ref",
    ),
    "kernel_open_support_bundle": (
        "support_bundle_ref",
        "safe_summary",
        "redaction_profile",
        "manifest_ref",
        "included_refs_ref",
        "redaction_report_ref",
    ),
}

RECOVERY_TOOL_OUTPUT_FIELDS: dict[str, tuple[str, ...]] = {
    tool_name: _RECOVERY_TOOL_OUTPUT_BASE + extra_fields
    for tool_name, extra_fields in _RECOVERY_TOOL_OUTPUT_EXTRA.items()
}

FORBIDDEN_AGENT_AUTHORED_FIELDS: frozenset[str] = frozenset(
    {
        "artifact_root_path",
        "collision_decision",
        "confirmation",
        "database_path",
        "file_list",
        "json_patch",
        "llm_output_text",
        "path",
        "payload",
        "raw_artifact_root",
        "raw_database_path",
        "raw_json",
        "raw_path",
        "selected_value",
        "target_path",
    }
)
