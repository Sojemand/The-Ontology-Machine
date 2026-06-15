from __future__ import annotations

from typing import Any, Mapping


REJECTED_OUTPUTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "kernel_apply_recovery_option": ("kernel.kernel_apply_recovery_option.output.v1", ("recovery_receipt_id", "next_kernel_event", "opened_dialog_ref", "support_bundle_ref")),
    "kernel_open_recovery_dialog": ("kernel.kernel_open_recovery_dialog.output.v1", ("recovery_receipt_id", "dialog_request_ref", "kernel_dialog_state")),
    "kernel_retry_recoverable_workflow": ("kernel.kernel_retry_recoverable_workflow.output.v1", ("new_or_resumed_workflow_run_id", "recovery_receipt_id", "progress_event_ref", "support_bundle_ref")),
    "kernel_resolve_stale_lock": ("kernel.kernel_resolve_stale_lock.output.v1", ("lock_id", "lock_status_after", "recovery_receipt_id", "support_bundle_ref")),
    "kernel_rebind_database_artifact_tree": ("kernel.kernel_rebind_database_artifact_tree.output.v1", ("binding_receipt_id", "recovery_receipt_id", "database_artifact_binding_ref", "support_bundle_ref")),
    "kernel_discard_or_archive_staged_work": ("kernel.kernel_discard_or_archive_staged_work.output.v1", ("archive_ref", "discard_receipt_id", "recovery_receipt_id", "support_bundle_ref")),
    "kernel_reconcile_partial_pipeline_run": ("kernel.kernel_reconcile_partial_pipeline_run.output.v1", ("reconciliation_receipt_id", "finalized_manifest_ref", "quarantine_ref", "new_recovery_event_ref", "support_bundle_ref")),
    "kernel_open_support_bundle": ("kernel.kernel_open_support_bundle.output.v1", ("support_bundle_ref", "safe_summary", "redaction_profile", "manifest_ref", "included_refs_ref", "redaction_report_ref")),
}

SERVICE_MISSING_OUTPUTS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "kernel_resolve_stale_lock": (
        "kernel.kernel_resolve_stale_lock.output.v1",
        ("lock_id", "lock_status_after", "recovery_receipt_id", "support_bundle_ref"),
        "recovery_receipt_id",
    ),
    "kernel_discard_or_archive_staged_work": (
        "kernel.kernel_discard_or_archive_staged_work.output.v1",
        ("archive_ref", "discard_receipt_id", "recovery_receipt_id", "support_bundle_ref"),
        "recovery_receipt_id",
    ),
    "kernel_reconcile_partial_pipeline_run": (
        "kernel.kernel_reconcile_partial_pipeline_run.output.v1",
        ("reconciliation_receipt_id", "finalized_manifest_ref", "quarantine_ref", "new_recovery_event_ref", "support_bundle_ref"),
        "reconciliation_receipt_id",
    ),
}


def rejected_output(tool_name: str, recovery_receipt_id: str | None, reason: str) -> dict[str, Any]:
    schema, fields = REJECTED_OUTPUTS.get(tool_name, REJECTED_OUTPUTS["kernel_open_support_bundle"])
    values = {field: None for field in fields}
    if "recovery_receipt_id" in values:
        values["recovery_receipt_id"] = recovery_receipt_id
    if "reconciliation_receipt_id" in values:
        values["reconciliation_receipt_id"] = recovery_receipt_id
    if tool_name == "kernel_apply_recovery_option":
        values["next_kernel_event"] = {"rejection_reason": reason}
    elif tool_name == "kernel_open_recovery_dialog":
        values["kernel_dialog_state"] = {"rejection_reason": reason}
    elif "safe_summary" in values:
        values["safe_summary"] = reason
    return tool_output(schema, "rejected", fields, values)


def service_missing_output(
    tool_name: str,
    *,
    receipt_id: str,
    support_bundle_ref: object,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    schema, fields, receipt_field = SERVICE_MISSING_OUTPUTS[tool_name]
    values = {field: extra.get(field) for field in fields}
    values[receipt_field] = receipt_id
    values["support_bundle_ref"] = support_bundle_ref
    return tool_output(schema, "support_only", fields, values)


def tool_output(schema_version: str, result_status: str, fields: tuple[str, ...], values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "result_status": result_status,
        **{field: values.get(field) for field in fields},
    }
