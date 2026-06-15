from __future__ import annotations

from semantic_control_kernel.types.agent_tools import AgentToolDefinition


def _recovery_definition(
    tool_name: str,
    description: str,
    outcome: str,
    does_not: str,
    recovery_class: str,
) -> AgentToolDefinition:
    return AgentToolDefinition(
        tool_name=tool_name,
        visibility="event_scoped",
        layer="recovery_control",
        description=description,
        outcome=outcome,
        does_not=does_not,
        implemented_by_phase=13,
        handler_status="event_scoped_until_phase_13",
        event_scoped_recovery_class=recovery_class,
    )


EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS: tuple[AgentToolDefinition, ...] = (
    _recovery_definition(
        "kernel_apply_recovery_option",
        "Applies one Kernel-authored recovery option from the current mirrored blocker or error.",
        "The selected recovery path is started, delegated to a Kernel dialog, or rejected if stale.",
        "Create new recovery actions or accept Agent-invented action IDs.",
        "recovery_option",
    ),
    _recovery_definition(
        "kernel_open_recovery_dialog",
        "Opens or reopens the Kernel/UI dialog required to fix a recoverable state.",
        "The correct Kernel dialog is visible again and bound to the current workflow and target identity.",
        "Let the Agent collect or validate the missing value in chat.",
        "recovery_dialog",
    ),
    _recovery_definition(
        "kernel_retry_recoverable_workflow",
        "Retries a recoverable workflow from the last Kernel-preserved safe state.",
        "The workflow is retried with preserved state, receipts and target identity.",
        "Retry destructive partial operations unless Kernel recovery policy marks the retry idempotent.",
        "retry",
    ),
    _recovery_definition(
        "kernel_resolve_stale_lock",
        "Resolves a stale lock after proving the owning operation is not live.",
        "The Kernel verifies owner liveness and releases, fails or preserves the lock.",
        "Force-unlock live operations or bypass target identity checks.",
        "stale_lock",
    ),
    _recovery_definition(
        "kernel_rebind_database_artifact_tree",
        "Repairs the binding between a Corpus database and its Artifact Tree.",
        "The Kernel validates the relationship and stores a corrected binding or blocks with support details.",
        "Guess bindings from similar paths or attach unrelated artifact trees.",
        "database_artifact_binding",
    ),
    _recovery_definition(
        "kernel_discard_or_archive_staged_work",
        "Discards or archives incomplete staged Kernel work after Kernel policy allows it.",
        "The Kernel archives or removes staged state according to policy and preserves audit references.",
        "Delete active production data without explicit Kernel confirmation.",
        "staged_work",
    ),
    _recovery_definition(
        "kernel_reconcile_partial_pipeline_run",
        "Reconciles partial Pipeline output after a run failed between steps.",
        "The Kernel finalizes safe evidence, quarantines partial output, or offers cleanup and reingest recovery.",
        "Silently treat partial data as complete.",
        "partial_pipeline_run",
    ),
    _recovery_definition(
        "kernel_open_support_bundle",
        "Opens or exposes a safe support bundle for final errors and unrecoverable states.",
        "Support bundle reference, relevant artifacts and safe technical summary become visible.",
        "Dump raw stack traces, secrets or full raw LLM responses into chat.",
        "support_bundle",
    ),
)

EVENT_SCOPED_RECOVERY_TOOL_NAMES = tuple(tool.tool_name for tool in EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS)
EVENT_SCOPED_RECOVERY_TOOL_MAP = {tool.tool_name: tool for tool in EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS}


def list_event_scoped_recovery_tool_definitions() -> tuple[AgentToolDefinition, ...]:
    return EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS


def get_event_scoped_recovery_tool(tool_name: str) -> AgentToolDefinition | None:
    return EVENT_SCOPED_RECOVERY_TOOL_MAP.get(tool_name)

