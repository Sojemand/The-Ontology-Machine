from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.debug.redaction import RedactionEngine
from semantic_control_kernel.repository.support_bundle_index_ops import default_severity
from semantic_control_kernel.types.recovery import SUPPORT_BUNDLE_REF_SCHEMA_VERSION


def manifest_payload(**values: Any) -> dict[str, Any]:
    return {
        "schema_version": "repository.support_bundle_manifest.v1",
        "support_bundle_id": values["bundle_id"],
        "trace_id": values["trace_id"],
        "created_at": values["created_at"],
        "category": values["category"],
        "severity": values["severity"] or default_severity(values["category"]),
        "workflow_run_id": values["workflow_run_id"],
        "workflow_tool": values["workflow_tool"],
        "safe_summary": values["safe_summary_text"],
        "included_refs": values["included_ref_payloads"],
        "redaction_profile": values["profile"],
        "retention_class": values["retention"],
        "redaction_report_ref": values["redaction_report_ref"],
    }


def add_optional_manifest_fields(manifest: dict[str, Any], *, redaction: RedactionEngine, profile: Mapping[str, Any], **values: Any) -> None:
    optional_fields = {
        "recovery_event_id": values["recovery_event_id"],
        "mirror_event_id": values["mirror_event_id"],
        "failed_kernel_step": values["failed_kernel_step"],
        "user_visible_cause": redaction.safe_summary(values["user_visible_cause"]) if values["user_visible_cause"] is not None else None,
        "state_snapshot_identity": dict(values["state_snapshot_identity"]) if values["state_snapshot_identity"] is not None else None,
        "target_identity_redacted": redaction.redact(dict(values["target_identity"] or {}), profile_id=profile["profile_id"])[0] if values["target_identity"] is not None else None,
        "what_was_preserved": redaction.safe_summary(values["what_was_preserved"]) if values["what_was_preserved"] is not None else None,
        "what_was_not_changed": redaction.safe_summary(values["what_was_not_changed"]) if values["what_was_not_changed"] is not None else None,
        "created_by": values["created_by"],
        "expires_at": values["expires_at"],
    }
    for key in RELATED_REF_KEYS:
        if values[key]:
            optional_fields[key] = [dict(item) for item in values[key]]
    for key, value in optional_fields.items():
        if value not in (None, [], {}):
            manifest[key] = value


def support_ref_payload(
    bundle_id: str,
    manifest_ref: str,
    created_at: str,
    category: str,
    workflow_run_id: str,
    recovery_event_id: str | None,
    safe_summary_text: str,
    included_ref_payloads: Sequence[Mapping[str, Any] | str],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SUPPORT_BUNDLE_REF_SCHEMA_VERSION,
        "support_bundle_id": bundle_id,
        "support_bundle_path": manifest_ref,
        "created_at": created_at,
        "category": category,
        "workflow_run_id": workflow_run_id,
        "recovery_event_id": recovery_event_id or "",
        "safe_summary": safe_summary_text,
        "included_refs": list(included_ref_payloads),
        "redaction_profile": dict(profile),
    }


RELATED_REF_KEYS = (
    "related_receipt_refs",
    "related_progress_event_refs",
    "related_mirror_event_refs",
    "related_recovery_refs",
    "adapter_call_diagnostic_refs",
    "llm_attempt_diagnostic_refs",
    "failed_attempt_artifact_refs",
)
