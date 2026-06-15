from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_types


_CONTRACT_TYPES = (
    ("TraceContext", "debug.trace_context.v1"),
    ("TraceLink", "debug.trace_link.v1"),
    ("AdapterCallDiagnostic", "debug.adapter_call_diagnostic.v1"),
    ("LLMAttemptDiagnostic", "debug.llm_attempt_diagnostic.v1"),
    ("RedactionReport", "debug.redaction_report.v1"),
    ("SupportBundleManifest", "repository.support_bundle_manifest.v1"),
    ("SupportBundleCleanupHistory", "debug.support_bundle_cleanup_history.v1"),
)

globals().update(make_contract_types(_CONTRACT_TYPES, __name__))


TRACE_CONTEXT_SCHEMA_VERSION = TraceContext.SCHEMA_VERSION
TRACE_LINK_SCHEMA_VERSION = TraceLink.SCHEMA_VERSION
ADAPTER_CALL_DIAGNOSTIC_SCHEMA_VERSION = AdapterCallDiagnostic.SCHEMA_VERSION
LLM_ATTEMPT_DIAGNOSTIC_SCHEMA_VERSION = LLMAttemptDiagnostic.SCHEMA_VERSION
REDACTION_REPORT_SCHEMA_VERSION = RedactionReport.SCHEMA_VERSION
SUPPORT_BUNDLE_MANIFEST_SCHEMA_VERSION = SupportBundleManifest.SCHEMA_VERSION
SUPPORT_BUNDLE_CLEANUP_HISTORY_SCHEMA_VERSION = SupportBundleCleanupHistory.SCHEMA_VERSION


TRACE_LINK_OBJECT_KINDS: tuple[str, ...] = (
    "workflow_run",
    "progress_event",
    "mirror_event",
    "interaction_request",
    "interaction_response",
    "confirmation_request",
    "confirmation_receipt",
    "operation_receipt",
    "recovery_event",
    "recovery_option",
    "recovery_receipt",
    "adapter_call_diagnostic",
    "llm_attempt_diagnostic",
    "llm_attempt_artifact",
    "support_bundle",
    "pipeline_batch_manifest",
    "merge_collision_manifest",
    "merge_id_map",
)

ADAPTER_DIAGNOSTIC_STATUSES: tuple[str, ...] = (
    "started",
    "succeeded",
    "blocked",
    "missing_capability",
    "timed_out",
    "failed",
    "uncertain_partial_mutation",
)

REDACTION_PROFILE_IDS: tuple[str, ...] = (
    "support_safe_v1",
    "user_visible_v1",
    "internal_ref_only_v1",
)

RETENTION_CLASSES: tuple[str, ...] = (
    "final_error_manual",
    "support_only_manual",
    "llm_validation_manual",
    "stale_recovery_90_days",
    "operator_snapshot_30_days",
    "test_fixture_disposable",
)
