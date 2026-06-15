from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.services.resume_options import RESUME_CONTINUE_TOOL_NAME
from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_NAMES
from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_NAMES
from semantic_control_kernel.types.agent_tools import (
    ALLOWED_INVOCATION_CONTEXT_FIELDS,
    REJECTED_LEGACY_AGENT_SURFACE_NAMES,
    find_forbidden_model_fields,
)


SUPPORT_CONTROL_TOOL_NAMES = (
    "kernel_status",
    "kernel_resume_state",
    "kernel_cancel_active_run",
    RESUME_CONTINUE_TOOL_NAME,
)


def rejected_fields(tool_name: str, context: Mapping[str, Any], model_payload: Mapping[str, Any]) -> tuple[str, ...]:
    rejected: set[str] = set()
    allowed_context = set(ALLOWED_INVOCATION_CONTEXT_FIELDS)
    allowed_model_payload: set[str] = set()
    if tool_name == RESUME_CONTINUE_TOOL_NAME:
        allowed_context.add("resume_option_ref")
        allowed_model_payload.add("resume_option_ref")
        _reject_non_string_resume_ref(context, rejected)
        _reject_non_string_resume_ref(model_payload, rejected)
    rejected.update(set(context) - allowed_context)
    if context.get("client_injected") is not None and context.get("client_injected") is not True:
        rejected.add("client_injected")
    rejected.update(find_forbidden_model_fields(context))
    if model_payload:
        rejected.update(set(model_payload) - allowed_model_payload)
        rejected.update(find_forbidden_model_fields({key: value for key, value in model_payload.items() if key not in allowed_model_payload}))
    return tuple(sorted(rejected))


def is_permanent_agent_tool_name(tool_name: str) -> bool:
    return tool_name in PERMANENT_AGENT_TOOL_NAMES


def is_rejected_legacy_agent_surface_name(tool_name: str) -> bool:
    return tool_name in REJECTED_LEGACY_AGENT_SURFACE_NAMES


def is_event_scoped_recovery_tool_name(tool_name: str) -> bool:
    return tool_name in EVENT_SCOPED_RECOVERY_TOOL_NAMES


def string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _reject_non_string_resume_ref(values: Mapping[str, Any], rejected: set[str]) -> None:
    if "resume_option_ref" in values and not isinstance(values.get("resume_option_ref"), str):
        rejected.add("resume_option_ref")
