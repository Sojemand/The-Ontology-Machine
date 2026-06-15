from __future__ import annotations

from typing import Any, Callable, Mapping

from semantic_control_kernel.domain.recovery.recovery_matrix import RecoveryMatrix
from semantic_control_kernel.types.enums import RecoveryActionType, RecoveryOwner, RiskClass
from semantic_control_kernel.types.recovery import RecoveryOption

OptionFactory = Callable[..., RecoveryOption]

STATIC_TOOL_OPTIONS: dict[str, dict[str, str]] = {
    "kernel_status": {
        "label": "Inspect Kernel status",
        "description": "Inspect whether the blocking owner is still active.",
        "owner": RecoveryOwner.AGENT_TOOL.value,
        "recovery_action_type": RecoveryActionType.INSPECT_RESUME_STATE.value,
        "effect": "inspect_status",
        "risk_class": RiskClass.READ_ONLY.value,
    },
    "kernel_retry_recoverable_workflow": {
        "label": "Retry workflow",
        "description": "Retry the workflow from the preserved safe state.",
        "owner": RecoveryOwner.AGENT_TOOL.value,
        "recovery_action_type": RecoveryActionType.RETRY_SAME_WORKFLOW.value,
        "effect": "retry_same_workflow",
        "risk_class": RiskClass.LONG_RUNNING.value,
    },
    "kernel_resolve_stale_lock": {
        "label": "Resolve stale lock",
        "description": "Verify owner liveness and update the lock only when safe.",
        "owner": RecoveryOwner.AGENT_TOOL.value,
        "recovery_action_type": RecoveryActionType.APPLY_KERNEL_OPTION.value,
        "effect": "resolve_stale_lock",
        "risk_class": RiskClass.NON_DESTRUCTIVE.value,
    },
    "kernel_rebind_database_artifact_tree": {
        "label": "Rebind database and Artifact Tree",
        "description": "Validate and repair the database-to-Artifact-Tree binding.",
        "owner": RecoveryOwner.AGENT_TOOL.value,
        "recovery_action_type": RecoveryActionType.APPLY_KERNEL_OPTION.value,
        "effect": "rebind_database_artifact_tree",
        "risk_class": RiskClass.NON_DESTRUCTIVE.value,
    },
    "kernel_reconcile_partial_pipeline_run": {
        "label": "Reconcile partial Pipeline run",
        "description": "Finalize safe evidence, quarantine partial output, or block with support.",
        "owner": RecoveryOwner.AGENT_TOOL.value,
        "recovery_action_type": RecoveryActionType.APPLY_KERNEL_OPTION.value,
        "effect": "reconcile_partial_pipeline_run",
        "risk_class": RiskClass.NON_DESTRUCTIVE.value,
    },
    "kernel_cancel_active_run": {
        "label": "Cancel active workflow",
        "description": "Cancel the active Kernel workflow when cancellation is still safe.",
        "owner": RecoveryOwner.AGENT_TOOL.value,
        "recovery_action_type": RecoveryActionType.CANCEL_ACTIVE_WORKFLOW.value,
        "effect": "cancel_active_workflow",
        "risk_class": RiskClass.NON_DESTRUCTIVE.value,
    },
    "kernel_resume_state": {
        "label": "Inspect resume state",
        "description": "Inspect preserved Kernel resume state for this workflow.",
        "owner": RecoveryOwner.AGENT_TOOL.value,
        "recovery_action_type": RecoveryActionType.INSPECT_RESUME_STATE.value,
        "effect": "inspect_resume_state",
        "risk_class": RiskClass.READ_ONLY.value,
    },
    "kernel_apply_recovery_option": {
        "label": "Apply bound recovery option",
        "description": "Apply the single Kernel-bound recovery option for this event.",
        "owner": RecoveryOwner.AGENT_TOOL.value,
        "recovery_action_type": RecoveryActionType.APPLY_KERNEL_OPTION.value,
        "effect": "apply_bound_recovery_option",
        "risk_class": RiskClass.NON_DESTRUCTIVE.value,
    },
}


def option_for_tool(
    tool: str,
    *,
    recovery_state: str,
    matrix: RecoveryMatrix,
    make_option: OptionFactory,
    base_kwargs: Mapping[str, Any],
    support_bundle_ref: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> RecoveryOption | None:
    if tool in STATIC_TOOL_OPTIONS:
        return make_option(**base_kwargs, **STATIC_TOOL_OPTIONS[tool], agent_tool=tool)
    if tool == "kernel_open_recovery_dialog":
        return make_option(
            **base_kwargs,
            label="Open recovery dialog",
            description="Open the Kernel-owned dialog for this recovery state.",
            owner=RecoveryOwner.KERNEL_DIALOG.value,
            recovery_action_type=RecoveryActionType.REOPEN_DIALOG.value,
            effect="open_kernel_recovery_dialog",
            risk_class=RiskClass.NON_DESTRUCTIVE.value,
            agent_tool=tool,
            kernel_dialog_action=matrix.get(recovery_state).direct_kernel_dialog,
        )
    if tool == "kernel_discard_or_archive_staged_work":
        destructive = bool(evidence.get("destructive_scope"))
        return make_option(
            **base_kwargs,
            label="Archive staged work",
            description="Archive or discard explicitly scoped incomplete staged work.",
            owner=RecoveryOwner.AGENT_TOOL.value,
            recovery_action_type=RecoveryActionType.DISCARD_OR_ARCHIVE_STAGED_WORK.value,
            effect="archive_staged_work",
            risk_class=RiskClass.DESTRUCTIVE.value if destructive else RiskClass.NON_DESTRUCTIVE.value,
            agent_tool=tool,
            requires_confirmation=destructive,
        )
    if tool == "kernel_open_support_bundle":
        return make_option(
            **base_kwargs,
            label="Open support bundle",
            description="Open safe technical support details for this recovery state.",
            owner=RecoveryOwner.SUPPORT_SURFACE.value,
            recovery_action_type=RecoveryActionType.OPEN_SUPPORT_BUNDLE.value,
            effect="open_support_bundle",
            risk_class=RiskClass.SUPPORT.value,
            agent_tool=tool,
            kernel_dialog_action="support_bundle_dialog",
            support_bundle_ref=support_bundle_ref,
        )
    if tool in {"create_custom_taxonomy_path", "create_custom_projection_path"}:
        return make_option(
            **base_kwargs,
            label=f"Continue with {tool}",
            description="Continue the incomplete staged Semantic Release through the Kernel-approved workflow entry.",
            owner=RecoveryOwner.AGENT_TOOL.value,
            recovery_action_type=RecoveryActionType.START_NEW_WORKFLOW.value,
            effect="continue_incomplete_staged_release",
            risk_class=RiskClass.LONG_RUNNING.value,
            agent_tool=tool,
            continuation_workflow_tool=tool,
            starts_new_workflow=True,
        )
    return None
