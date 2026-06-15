from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.enums import DialogType, InteractionKind, MirrorEventType, MirrorSeverity
from semantic_control_kernel.types.events import ProgressEvent
from semantic_control_kernel.validation.contract_validation import KernelContractError, serialize_contract
from semantic_control_kernel.validation.recovery_validation import assert_recovery_mirror_event

INTERACTION_MIRROR_MAPPING: dict[tuple[str, str | None], tuple[str, str, str]] = {
    (InteractionKind.INPUT.value, None): (
        MirrorEventType.INPUT_DIALOG_OPENED.value,
        MirrorSeverity.INFO.value,
        "open",
    ),
    (InteractionKind.SELECTION.value, None): (
        MirrorEventType.SELECTION_DIALOG_OPENED.value,
        MirrorSeverity.INFO.value,
        "open",
    ),
    (InteractionKind.CONFIRMATION.value, None): (
        MirrorEventType.CONFIRMATION_DIALOG_OPENED.value,
        MirrorSeverity.INFO.value,
        "open",
    ),
    (InteractionKind.RECOVERY.value, None): (
        MirrorEventType.RECOVERY_STATE.value,
        MirrorSeverity.RECOVERABLE_ERROR.value,
        "open",
    ),
    (InteractionKind.NOTICE.value, DialogType.BLOCKER_NOTICE.value): (
        MirrorEventType.BLOCKER.value,
        MirrorSeverity.WARNING.value,
        "not_required",
    ),
    (InteractionKind.NOTICE.value, DialogType.PROGRESS_NOTICE.value): (
        MirrorEventType.PROGRESS.value,
        MirrorSeverity.INFO.value,
        "not_required",
    ),
    (InteractionKind.NOTICE.value, DialogType.SUPPORT_BUNDLE_NOTICE.value): (
        MirrorEventType.LLM_VALIDATION_FAILED_FINAL.value,
        MirrorSeverity.FINAL_ERROR.value,
        "not_required",
    ),
}


def mirror_values_for_request(payload: Mapping[str, Any]) -> tuple[str, str, str]:
    kind = str(payload["interaction_kind"])
    dialog_type = str(payload.get("dialog_type"))
    return INTERACTION_MIRROR_MAPPING.get((kind, dialog_type)) or INTERACTION_MIRROR_MAPPING[(kind, None)]


def progress_payload(progress_event: ProgressEvent | Mapping[str, Any] | None) -> dict[str, Any] | None:
    if progress_event is None:
        return None
    if isinstance(progress_event, ProgressEvent):
        return serialize_contract(progress_event)
    return dict(progress_event)


def validate_event_scoped_tool_exposure(
    *,
    allowed_agent_tools: Sequence[str],
    recovery_options: Sequence[Mapping[str, Any]] | None,
    is_kernel_auto_call: bool,
) -> None:
    tools = [tool for tool in allowed_agent_tools if str(tool).strip()]
    if not tools:
        return
    if not is_kernel_auto_call:
        raise KernelContractError("Event-scoped Agent tools require a Kernel auto-call mirror event.")
    options = list(recovery_options or ())
    if not options:
        raise KernelContractError("Event-scoped Agent tools require Kernel-authored recovery_options.")
    option_tools = {
        str(option.get("agent_tool"))
        for option in options
        if isinstance(option, Mapping) and isinstance(option.get("agent_tool"), str)
    }
    if option_tools:
        missing = [tool for tool in tools if tool not in option_tools]
        if missing:
            raise KernelContractError(
                "Event-scoped Agent tools must be bound to recovery_options: "
                + ", ".join(missing)
            )


def expires_in(ttl_seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z")
