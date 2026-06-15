from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.surface.recovery_tool_outputs import service_missing_output
from semantic_control_kernel.types.enums import RecoveryResultStatus


def open_support_bundle_output(
    support_bundle_store: SupportBundleStore,
    recovery_event: Mapping[str, Any],
) -> dict[str, Any]:
    support = recovery_event.get("support_bundle_ref") or {}
    open_payload = _open_bundle_payload(support_bundle_store, support)
    opened = open_payload if isinstance(open_payload, Mapping) else {}
    return {
        "schema_version": "kernel.kernel_open_support_bundle.output.v1",
        "result_status": "applied" if support else "support_only",
        "support_bundle_ref": opened.get("support_bundle_ref", support),
        "safe_summary": opened.get("safe_summary", support.get("safe_summary") if isinstance(support, Mapping) else None),
        "redaction_profile": opened.get("redaction_profile", support.get("redaction_profile") if isinstance(support, Mapping) else None),
        "manifest_ref": opened.get("manifest_ref"),
        "included_refs_ref": opened.get("included_refs_ref"),
        "redaction_report_ref": opened.get("redaction_report_ref"),
    }


def service_missing_recovery_output(
    recovery_store: RecoveryEventStore,
    tool_name: str,
    recovery_event: Mapping[str, Any],
    recovery_id: str,
    **extra: Any,
) -> dict[str, Any]:
    receipt = recovery_store.append_recovery_receipt(
        recovery_event=recovery_event,
        recovery_id=recovery_id,
        result_status=RecoveryResultStatus.SUPPORT_ONLY.value,
        selected_recovery_option={"reason": "service_not_configured"},
    )
    return service_missing_output(
        tool_name,
        receipt_id=receipt.payload["recovery_receipt_id"],
        support_bundle_ref=recovery_event.get("support_bundle_ref"),
        extra=extra,
    )


def _open_bundle_payload(support_bundle_store: SupportBundleStore, support: object) -> Mapping[str, Any] | None:
    if not isinstance(support, Mapping) or not isinstance(support.get("support_bundle_id"), str) or not support.get("support_bundle_id"):
        return None
    try:
        return support_bundle_store.get_open_bundle_payload(str(support["support_bundle_id"]))
    except Exception:
        return None
