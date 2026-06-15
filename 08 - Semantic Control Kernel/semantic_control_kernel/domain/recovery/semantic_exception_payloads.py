from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.recovery_context import RecoveryContext
from semantic_control_kernel.domain.recovery.semantic_exception_policy import (
    agent_guidance,
    mirror_event_type_for,
    progress_status,
    recovery_event_status,
)
from semantic_control_kernel.domain.recovery.semantic_exception_types import SemanticRecoveryException
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import MirrorSeverity, ProgressEventType
from semantic_control_kernel.types.events import ProgressEvent
from semantic_control_kernel.types.recovery import RECOVERY_EVENT_SCHEMA_VERSION


def create_support_ref(
    support_bundle_service,
    *,
    context: RecoveryContext,
    exc: SemanticRecoveryException,
    recovery_state: str,
    recovery_event_id: str,
) -> Mapping[str, Any]:
    return support_bundle_service.create_support_bundle(
        category=recovery_state,
        workflow_run_id=context.workflow_run_id,
        recovery_event_id=recovery_event_id,
        summary=exc.user_visible_cause,
        included_refs=context.support_refs,
        technical_context=exc.technical_context,
    ).to_dict()


def create_mirror_event(
    service: KernelMirrorEventService,
    *,
    context: RecoveryContext,
    exc: SemanticRecoveryException,
    recovery_state: str,
    options,
    allowed_tools: tuple[str, ...],
    support_ref: Mapping[str, Any] | None,
    expires_at: str | None,
):
    return service.create_mirror_event(
        event_type=mirror_event_type_for(recovery_state),
        severity=_mirror_severity(recovery_state),
        user_visible_summary=exc.user_visible_cause,
        current_state_summary=f"{context.workflow_tool}:{context.failed_kernel_step} is blocked by {recovery_state}.",
        workflow_run_id=context.workflow_run_id,
        workflow_tool=context.workflow_tool,
        user_visible_cause=exc.cause_code,
        recovery_options=[option.to_dict() for option in options],
        allowed_agent_tools=allowed_tools,
        support_bundle_ref=support_ref,
        agent_explanation_guidance=agent_guidance(recovery_state),
        tool_availability_expires_at=expires_at,
    )


def recovery_event_payload(
    *,
    context: RecoveryContext,
    exc: SemanticRecoveryException,
    recovery_state: str,
    recovery_event_id: str,
    mirror_event_id: str,
    options,
    allowed_tools: tuple[str, ...],
    support_ref: Mapping[str, Any] | None,
    expires_at: str | None,
) -> dict[str, Any]:
    return {
        "allowed_agent_tools": list(allowed_tools),
        "blocked_functions": list(exc.blocked_functions or context.blocked_functions),
        "cause_code": exc.cause_code,
        "created_at": utc_iso(),
        "detected_by": context.detected_by,
        "expires_at": expires_at,
        "failed_kernel_step": context.failed_kernel_step,
        "mirror_event_id": mirror_event_id,
        "recovery_event_id": recovery_event_id,
        "recovery_options": [option.to_dict() for option in options],
        "recovery_state": recovery_state,
        "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
        "state_snapshot_identity": context.snapshot_payload(),
        "status": recovery_event_status(recovery_state),
        "superseded_by": None,
        "support_bundle_ref": support_ref,
        "target_identity": context.target_payload(),
        "user_visible_cause": exc.user_visible_cause,
        "workflow_run_id": context.workflow_run_id,
        "workflow_tool": context.workflow_tool,
    }


def progress_event(
    *,
    context: RecoveryContext,
    exc: SemanticRecoveryException,
    recovery_state: str,
    recovery_event_id: str,
    recovery_receipt_id: str,
) -> ProgressEvent:
    return ProgressEvent.from_dict(
        {
            "current_state_summary": f"Recovery event {recovery_event_id} persisted.",
            "event_type": ProgressEventType.RECOVERY_STEP.value,
            "receipt_refs": [{"recovery_receipt_id": recovery_receipt_id}],
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "sequence_index": 0,
            "status": progress_status(recovery_state),
            "step_id": context.failed_kernel_step,
            "step_label": "Semantic recovery",
            "timestamp": utc_iso(),
            "user_visible_summary": exc.user_visible_cause,
            "workflow_run_id": context.workflow_run_id,
            "workflow_tool": context.workflow_tool,
        }
    )


def _mirror_severity(recovery_state: str) -> str:
    from semantic_control_kernel.types.enums import RecoveryStateClass

    if recovery_state == RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value:
        return MirrorSeverity.FINAL_ERROR.value
    return MirrorSeverity.RECOVERABLE_ERROR.value
