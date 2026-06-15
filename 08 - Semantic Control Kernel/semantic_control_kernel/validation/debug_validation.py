from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.types.debug import (
    ADAPTER_CALL_DIAGNOSTIC_SCHEMA_VERSION,
    ADAPTER_DIAGNOSTIC_STATUSES,
    LLM_ATTEMPT_DIAGNOSTIC_SCHEMA_VERSION,
    REDACTION_PROFILE_IDS,
    REDACTION_REPORT_SCHEMA_VERSION,
    RETENTION_CLASSES,
    SUPPORT_BUNDLE_CLEANUP_HISTORY_SCHEMA_VERSION,
    SUPPORT_BUNDLE_MANIFEST_SCHEMA_VERSION,
    TRACE_CONTEXT_SCHEMA_VERSION,
    TRACE_LINK_OBJECT_KINDS,
    TRACE_LINK_SCHEMA_VERSION,
)
from semantic_control_kernel.validation.contract_validation import KernelContractError
from semantic_control_kernel.validation.debug_validation_helpers import (
    ensure_enum,
    ensure_mapping,
    ensure_sequence,
    ensure_sequence_of_mappings_or_strings,
    validate_closed_payload,
)
from semantic_control_kernel.validation.debug_validation_schema import (
    ADAPTER_DIAGNOSTIC_OPTIONAL_FIELDS,
    ADAPTER_DIAGNOSTIC_REQUIRED_FIELDS,
    LLM_ATTEMPT_DIAGNOSTIC_REQUIRED_FIELDS,
    REDACTION_REPORT_REQUIRED_FIELDS,
    SUPPORT_BUNDLE_CLEANUP_HISTORY_REQUIRED_FIELDS,
    SUPPORT_BUNDLE_MANIFEST_OPTIONAL_FIELDS,
    SUPPORT_BUNDLE_MANIFEST_REQUIRED_FIELDS,
    TRACE_CONTEXT_OPTIONAL_FIELDS,
    TRACE_CONTEXT_REQUIRED_FIELDS,
    TRACE_LINK_REQUIRED_FIELDS,
)

def validate_trace_context(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(
        payload,
        TRACE_CONTEXT_SCHEMA_VERSION,
        TRACE_CONTEXT_REQUIRED_FIELDS,
        TRACE_CONTEXT_OPTIONAL_FIELDS,
    )
    ensure_sequence_of_mappings_or_strings(payload.get("related_analysis_run_ids"), "debug.trace_context.v1.related_analysis_run_ids", allow_none=True)


def validate_trace_link(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(
        payload,
        TRACE_LINK_SCHEMA_VERSION,
        TRACE_LINK_REQUIRED_FIELDS,
    )
    ensure_enum(payload["object_kind"], TRACE_LINK_OBJECT_KINDS, "debug.trace_link.v1.object_kind")


def validate_adapter_call_diagnostic(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(
        payload,
        ADAPTER_CALL_DIAGNOSTIC_SCHEMA_VERSION,
        ADAPTER_DIAGNOSTIC_REQUIRED_FIELDS,
        ADAPTER_DIAGNOSTIC_OPTIONAL_FIELDS,
    )
    ensure_enum(payload["status"], ADAPTER_DIAGNOSTIC_STATUSES, "debug.adapter_call_diagnostic.v1.status")
    ensure_mapping(payload["redaction_profile"], "debug.adapter_call_diagnostic.v1.redaction_profile")


def validate_llm_attempt_diagnostic(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(
        payload,
        LLM_ATTEMPT_DIAGNOSTIC_SCHEMA_VERSION,
        LLM_ATTEMPT_DIAGNOSTIC_REQUIRED_FIELDS,
    )
    ensure_mapping(payload["artifact_refs"], "debug.llm_attempt_diagnostic.v1.artifact_refs")
    ensure_mapping(payload["redaction_profile"], "debug.llm_attempt_diagnostic.v1.redaction_profile")


def validate_redaction_report(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(
        payload,
        REDACTION_REPORT_SCHEMA_VERSION,
        REDACTION_REPORT_REQUIRED_FIELDS,
    )
    ensure_mapping(payload["redaction_profile"], "debug.redaction_report.v1.redaction_profile")
    ensure_mapping(payload["redacted_field_counts"], "debug.redaction_report.v1.redacted_field_counts")
    ensure_mapping(payload["redacted_path_counts"], "debug.redaction_report.v1.redacted_path_counts")
    ensure_mapping(payload["redacted_secret_counts"], "debug.redaction_report.v1.redacted_secret_counts")
    ensure_sequence(payload["raw_payload_refs_excluded"], "debug.redaction_report.v1.raw_payload_refs_excluded")


def validate_support_bundle_manifest(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(
        payload,
        SUPPORT_BUNDLE_MANIFEST_SCHEMA_VERSION,
        SUPPORT_BUNDLE_MANIFEST_REQUIRED_FIELDS,
        SUPPORT_BUNDLE_MANIFEST_OPTIONAL_FIELDS,
    )
    ensure_mapping(payload["redaction_profile"], "repository.support_bundle_manifest.v1.redaction_profile")
    ensure_sequence(payload["included_refs"], "repository.support_bundle_manifest.v1.included_refs")
    ensure_enum(payload["retention_class"], RETENTION_CLASSES, "repository.support_bundle_manifest.v1.retention_class")


def validate_support_bundle_cleanup_history(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(
        payload,
        SUPPORT_BUNDLE_CLEANUP_HISTORY_SCHEMA_VERSION,
        SUPPORT_BUNDLE_CLEANUP_HISTORY_REQUIRED_FIELDS,
    )
    ensure_sequence(payload["deleted_bundle_ids"], "debug.support_bundle_cleanup_history.v1.deleted_bundle_ids")
    ensure_sequence(payload["retained_bundle_ids"], "debug.support_bundle_cleanup_history.v1.retained_bundle_ids")
    ensure_sequence(payload["expired_bundle_ids"], "debug.support_bundle_cleanup_history.v1.expired_bundle_ids")
    if not isinstance(payload["dry_run"], bool):
        raise KernelContractError("debug.support_bundle_cleanup_history.v1.dry_run must be boolean.")


def validate_redaction_profile(payload: Mapping[str, Any]) -> None:
    ensure_mapping(payload, "redaction_profile")
    profile_id = payload.get("profile_id")
    if not isinstance(profile_id, str):
        raise KernelContractError("redaction_profile.profile_id must be a string.")
    ensure_enum(profile_id, REDACTION_PROFILE_IDS, "redaction_profile.profile_id")
