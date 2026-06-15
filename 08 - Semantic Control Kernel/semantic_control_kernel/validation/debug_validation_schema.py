from __future__ import annotations


TRACE_CONTEXT_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "trace_id",
    "workflow_run_id",
    "workflow_tool",
    "created_at",
    "started_by",
    "root_target_identity_ref",
    "state_root_ref",
)

TRACE_CONTEXT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "parent_trace_id",
    "active_recovery_event_id",
    "active_mirror_event_id",
    "active_support_bundle_id",
    "related_pipeline_run_id",
    "related_analysis_run_ids",
)

TRACE_LINK_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "trace_id",
    "workflow_run_id",
    "object_kind",
    "object_id",
    "object_ref",
    "created_at",
)

ADAPTER_DIAGNOSTIC_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "adapter_call_id",
    "trace_id",
    "workflow_run_id",
    "adapter_name",
    "owner_module",
    "owner_action",
    "status",
    "started_at",
    "finished_at",
    "duration_ms",
    "safe_summary",
    "request_ref",
    "response_ref",
    "redaction_profile",
)

ADAPTER_DIAGNOSTIC_OPTIONAL_FIELDS: tuple[str, ...] = (
    "error_code",
    "error_category",
    "retry_count",
    "timeout_seconds",
    "exit_code",
    "target_identity_hash",
    "artifact_refs",
    "receipt_refs",
    "count_summaries",
    "request_schema_version",
    "response_schema_version",
)

LLM_ATTEMPT_DIAGNOSTIC_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "llm_attempt_id",
    "trace_id",
    "workflow_run_id",
    "analysis_run_id",
    "llm_function_name",
    "attempt_index",
    "max_attempts",
    "attempted_schema",
    "parse_status",
    "validation_status",
    "validation_error_summary",
    "artifact_refs",
    "created_at",
    "redaction_profile",
)

REDACTION_REPORT_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "support_bundle_id",
    "redaction_profile",
    "redacted_field_counts",
    "redacted_path_counts",
    "redacted_secret_counts",
    "raw_payload_refs_excluded",
    "created_at",
)

SUPPORT_BUNDLE_MANIFEST_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "support_bundle_id",
    "trace_id",
    "created_at",
    "category",
    "severity",
    "workflow_run_id",
    "workflow_tool",
    "safe_summary",
    "included_refs",
    "redaction_profile",
    "retention_class",
)

SUPPORT_BUNDLE_MANIFEST_OPTIONAL_FIELDS: tuple[str, ...] = (
    "failed_kernel_step",
    "recovery_event_id",
    "mirror_event_id",
    "error_code",
    "error_category",
    "user_visible_cause",
    "target_identity_redacted",
    "state_snapshot_identity",
    "what_was_preserved",
    "what_was_not_changed",
    "related_receipt_refs",
    "related_progress_event_refs",
    "related_mirror_event_refs",
    "related_recovery_refs",
    "adapter_call_diagnostic_refs",
    "llm_attempt_diagnostic_refs",
    "failed_attempt_artifact_refs",
    "support_only",
    "redaction_report_ref",
    "expires_at",
    "created_by",
)

SUPPORT_BUNDLE_CLEANUP_HISTORY_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "cleanup_id",
    "created_at",
    "operator_reason",
    "deleted_bundle_ids",
    "retained_bundle_ids",
    "expired_bundle_ids",
    "dry_run",
)
