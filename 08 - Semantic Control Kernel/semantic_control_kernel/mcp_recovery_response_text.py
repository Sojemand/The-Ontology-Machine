from __future__ import annotations

from typing import Any, Mapping


def recovery_applied_summary(tool_name: str) -> str:
    if tool_name == "kernel_open_recovery_dialog":
        return "The Kernel reopened the recovery dialog for the active workflow state."
    if tool_name == "kernel_open_support_bundle":
        return "The Kernel exposed the support bundle for the active recovery event."
    return "The Kernel applied the selected recovery action."


def recovery_support_only_summary(tool_name: str, output: Mapping[str, Any]) -> str:
    if tool_name == "kernel_open_support_bundle":
        safe_summary = output.get("safe_summary")
        if isinstance(safe_summary, str) and safe_summary.strip():
            return safe_summary
        return "The Kernel exposed the support bundle for the active recovery event."
    return "The Kernel kept the workflow in a support-only recovery state for this request."


def recovery_rejected_summary(output: Mapping[str, Any]) -> str:
    if recovery_rejection_reason(output):
        return "The selected recovery action is no longer available in the current Kernel state."
    return "The selected recovery action could not be applied."


def recovery_rejection_reason(output: Mapping[str, Any]) -> str:
    for field_name in ("next_kernel_event", "kernel_dialog_state"):
        value = output.get(field_name)
        if isinstance(value, Mapping):
            reason = value.get("rejection_reason")
            if isinstance(reason, str) and reason.strip():
                return reason
    safe_summary = output.get("safe_summary")
    if isinstance(safe_summary, str) and safe_summary.strip():
        return safe_summary
    return ""
