from __future__ import annotations

from typing import Any, Mapping


def final_recovery_options(preserved_state_summary: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    options = [
        {
            "recovery_id": "support_only",
            "owner": "support_surface",
            "recovery_action_type": "open_support_bundle",
            "agent_tool": "kernel_open_support_bundle",
        }
    ]
    tools = ["kernel_open_support_bundle"]
    if preserved_state_summary.get("safe_to_retry") is True:
        options.insert(
            0,
            {
                "recovery_id": "retry_same_workflow",
                "owner": "agent_tool",
                "recovery_action_type": "retry_same_workflow",
                "agent_tool": "kernel_retry_recoverable_workflow",
            },
        )
        tools.insert(0, "kernel_retry_recoverable_workflow")
    if preserved_state_summary.get("resumable_state") is True:
        options.append(
            {
                "recovery_id": "inspect_resume_state",
                "owner": "agent_tool",
                "recovery_action_type": "inspect_resume_state",
                "agent_tool": "kernel_resume_state",
            }
        )
        tools.append("kernel_resume_state")
    if preserved_state_summary.get("cancellable") is True:
        options.append(
            {
                "recovery_id": "cancel_active_workflow",
                "owner": "agent_tool",
                "recovery_action_type": "cancel_active_workflow",
                "agent_tool": "kernel_cancel_active_run",
            }
        )
        tools.append("kernel_cancel_active_run")
    bound_recovery = preserved_state_summary.get("bound_recovery_option")
    if isinstance(bound_recovery, Mapping):
        option = {
            "recovery_id": str(bound_recovery.get("recovery_id", "bound_recovery_option")),
            "owner": str(bound_recovery.get("owner", "kernel")),
            "recovery_action_type": str(bound_recovery.get("recovery_action_type", "apply_recovery_option")),
            "agent_tool": "kernel_apply_recovery_option",
        }
        if "label" in bound_recovery:
            option["label"] = bound_recovery["label"]
        if "description" in bound_recovery:
            option["description"] = bound_recovery["description"]
        options.append(option)
        tools.append("kernel_apply_recovery_option")
    return options, tools
