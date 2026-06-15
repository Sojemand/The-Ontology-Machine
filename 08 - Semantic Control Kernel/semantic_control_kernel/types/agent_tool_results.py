from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.agent_tool_constants import (
    AGENT_TOOL_INVOCATION_SCHEMA_VERSION,
    AGENT_TOOL_RESULT_SCHEMA_VERSION,
    FORBIDDEN_MODEL_AUTHORED_FIELDS,
)
from semantic_control_kernel.types.agent_tool_definitions import _copy_mapping


@dataclass(frozen=True)
class AgentToolInvocation:
    tool_name: str
    invocation_context: dict[str, Any]
    model_payload_status: str
    mirror_event_id: str | None = None
    client_request_id: str | None = None
    user_request_ref: str | None = None
    schema_version: str = AGENT_TOOL_INVOCATION_SCHEMA_VERSION

    @classmethod
    def from_values(
        cls,
        *,
        tool_name: str,
        invocation_context: Mapping[str, Any] | None = None,
        model_payload_status: str,
        mirror_event_id: str | None = None,
        client_request_id: str | None = None,
        user_request_ref: str | None = None,
    ) -> "AgentToolInvocation":
        return cls(
            tool_name=tool_name,
            invocation_context=_copy_mapping(invocation_context or {}),
            model_payload_status=model_payload_status,
            mirror_event_id=mirror_event_id,
            client_request_id=client_request_id,
            user_request_ref=user_request_ref,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "tool_name": self.tool_name,
            "invocation_context": _copy_mapping(self.invocation_context),
            "model_payload_status": self.model_payload_status,
        }
        for key in ("mirror_event_id", "client_request_id", "user_request_ref"):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload


@dataclass(frozen=True)
class AgentToolResult:
    tool_name: str
    status: str
    effect: str
    user_visible_summary: str
    workflow_run_id: str | None = None
    mirror_event: Mapping[str, Any] | None = None
    resume_state: Mapping[str, Any] | None = None
    active_state: Mapping[str, Any] | None = None
    error: Mapping[str, Any] | None = None
    implemented_by_phase: int | None = None
    schema_version: str = AGENT_TOOL_RESULT_SCHEMA_VERSION
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "tool_name": self.tool_name,
            "status": self.status,
            "effect": self.effect,
            "user_visible_summary": self.user_visible_summary,
        }
        optional_values = {
            "workflow_run_id": self.workflow_run_id,
            "mirror_event": _copy_mapping(self.mirror_event) if self.mirror_event is not None else None,
            "resume_state": _copy_mapping(self.resume_state) if self.resume_state is not None else None,
            "active_state": _copy_mapping(self.active_state) if self.active_state is not None else None,
            "error": _copy_mapping(self.error) if self.error is not None else None,
            "implemented_by_phase": self.implemented_by_phase,
        }
        for key, value in optional_values.items():
            if value is not None:
                payload[key] = value
        payload.update(_copy_mapping(self.extra))
        return payload


def rejected_result(tool_name: str, code: str, message: str, **details: Any) -> AgentToolResult:
    error: dict[str, Any] = {"code": code, "message": message}
    error.update({key: value for key, value in details.items() if value is not None})
    return AgentToolResult(tool_name=tool_name, status="rejected", effect="none", user_visible_summary=message, error=error)


def blocked_result(tool_name: str, *, code: str, message: str, implemented_by_phase: int | None = None, active_state: Mapping[str, Any] | None = None) -> AgentToolResult:
    return AgentToolResult(
        tool_name=tool_name,
        status="blocked",
        effect="none",
        user_visible_summary=message,
        error={"code": code, "message": message},
        implemented_by_phase=implemented_by_phase,
        active_state=active_state,
    )


def ok_result(
    tool_name: str,
    *,
    effect: str,
    user_visible_summary: str,
    resume_state: Mapping[str, Any] | None = None,
    active_state: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> AgentToolResult:
    return AgentToolResult(
        tool_name=tool_name,
        status="ok",
        effect=effect,
        user_visible_summary=user_visible_summary,
        resume_state=resume_state,
        active_state=active_state,
        extra=extra or {},
    )


def find_forbidden_model_fields(payload: Mapping[str, Any] | Sequence[Any] | object) -> tuple[str, ...]:
    found: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_MODEL_AUTHORED_FIELDS:
                    found.add(str(key))
                walk(child)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                walk(item)

    walk(payload)
    return tuple(sorted(found))
