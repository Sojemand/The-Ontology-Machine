from __future__ import annotations

from typing import Mapping

from semantic_control_kernel.domain.recovery.semantic_exception_types import SemanticRecoveryException
from semantic_control_kernel.types.enums import MirrorEventType, ProgressStatus, RecoveryResultStatus, RecoveryStateClass


def needs_support_bundle(recovery_state: str, exc: SemanticRecoveryException) -> bool:
    return recovery_state in {
        RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value,
        RecoveryStateClass.PARTIAL_PIPELINE_RUN.value,
    } or bool(exc.technical_context.get("support_bundle_required"))


def mirror_event_type_for(recovery_state: str) -> str:
    if recovery_state == RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value:
        return MirrorEventType.LLM_VALIDATION_FAILED_FINAL.value
    if recovery_state in {
        RecoveryStateClass.PARTIAL_PIPELINE_RUN.value,
        RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value,
    }:
        return MirrorEventType.PIPELINE_ERROR.value
    return MirrorEventType.RECOVERY_STATE.value


def agent_guidance(recovery_state: str) -> str:
    if recovery_state == RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value:
        return "Explain the final validation failure only from Kernel-provided retry, cancel, resume or support options."
    return "Explain only the mirrored cause and Kernel-authored recovery options."


def recovery_status(recovery_state: str) -> str:
    return "support_only" if recovery_state == RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value else "blocked"


def recovery_event_status(recovery_state: str) -> str:
    return "support_only" if recovery_state == RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value else "active"


def recovery_result_status(recovery_state: str) -> str:
    if recovery_state == RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value:
        return RecoveryResultStatus.SUPPORT_ONLY.value
    return RecoveryResultStatus.REJECTED.value


def progress_status(recovery_state: str) -> str:
    if recovery_state == RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value:
        return ProgressStatus.FAILED.value
    return ProgressStatus.BLOCKED.value


def allowed_tools_from_options(options) -> tuple[str, ...]:
    return tuple(
        option.payload["agent_tool"]
        for option in options
        if isinstance(option.payload.get("agent_tool"), str) and option.payload["agent_tool"]
    )


def maybe_support_ref(payload: Mapping[str, object] | None) -> Mapping[str, object] | None:
    return payload if payload else None
