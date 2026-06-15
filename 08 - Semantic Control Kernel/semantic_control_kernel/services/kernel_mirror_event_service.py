from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.types.enums import (
    InteractionKind,
    MirrorSeverity,
    MirrorSource,
    RiskClass,
)
from semantic_control_kernel.types.events import MirrorEvent, ProgressEvent, UserInteractionRequest
from semantic_control_kernel.validation.contract_validation import KernelContractError
from semantic_control_kernel.validation.recovery_validation import assert_recovery_mirror_event

from .kernel_mirror_event_policy import (
    expires_in,
    mirror_values_for_request,
    progress_payload,
    validate_event_scoped_tool_exposure,
)


class KernelMirrorEventService:
    def __init__(self, store: MirrorEventStore) -> None:
        self.store = store

    def create_mirror_event(
        self,
        *,
        event_type: str,
        severity: str,
        user_visible_summary: str,
        current_state_summary: str,
        mirror_event_id: str | None = None,
        is_kernel_auto_call: bool = True,
        workflow_run_id: str | None = None,
        workflow_tool: str | None = None,
        user_visible_cause: str | None = None,
        kernel_dialog_state: str | None = None,
        recovery_options: Sequence[Mapping[str, Any]] | None = None,
        allowed_agent_tools: Sequence[str] | None = None,
        agent_explanation_guidance: str | None = None,
        technical_detail_ref: Mapping[str, Any] | None = None,
        support_bundle_ref: Mapping[str, Any] | None = None,
        progress_event: ProgressEvent | Mapping[str, Any] | None = None,
        tool_availability_expires_at: str | None = None,
    ) -> MirrorEvent:
        validate_event_scoped_tool_exposure(
            allowed_agent_tools=allowed_agent_tools or (),
            recovery_options=recovery_options,
            is_kernel_auto_call=is_kernel_auto_call,
        )
        mirror_id = mirror_event_id or generate_id("mirror_event_id")
        payload: dict[str, Any] = {
            "current_state_summary": current_state_summary,
            "event_type": event_type,
            "is_kernel_auto_call": is_kernel_auto_call,
            "mirror_event_id": mirror_id,
            "mirror_source": MirrorSource.KERNEL.value,
            "schema_version": MirrorEvent.SCHEMA_VERSION,
            "severity": severity,
            "user_visible_summary": user_visible_summary,
        }
        optional_values = {
            "workflow_run_id": workflow_run_id,
            "workflow_tool": workflow_tool,
            "user_visible_cause": user_visible_cause,
            "kernel_dialog_state": kernel_dialog_state,
            "recovery_options": list(recovery_options) if recovery_options is not None else None,
            "allowed_agent_tools": list(allowed_agent_tools or ()),
            "agent_explanation_guidance": agent_explanation_guidance,
            "technical_detail_ref": dict(technical_detail_ref) if technical_detail_ref is not None else None,
            "support_bundle_ref": dict(support_bundle_ref) if support_bundle_ref is not None else None,
            "progress_event": progress_payload(progress_event),
        }
        for key, value in optional_values.items():
            if value is not None:
                payload[key] = value
        if "recovery_options" in payload or payload.get("allowed_agent_tools"):
            assert_recovery_mirror_event(payload)
        event = MirrorEvent.from_dict(payload)
        self.store.append_mirror_event(event)
        if allowed_agent_tools:
            self.store.put_tool_availability(
                mirror_id,
                allowed_agent_tools,
                tool_availability_expires_at or expires_in(1800),
            )
        return event

    def create_for_interaction_request(
        self,
        request: UserInteractionRequest,
        *,
        allowed_agent_tools: Sequence[str] | None = None,
        tool_availability_expires_at: str | None = None,
    ) -> MirrorEvent:
        payload = request.to_dict()
        if allowed_agent_tools and payload["interaction_kind"] != InteractionKind.RECOVERY.value:
            raise KernelContractError(
                "Event-scoped Agent tools may be exposed only by recovery-capable Kernel mirror events."
            )
        event_type, severity, dialog_state = mirror_values_for_request(payload)
        if payload.get("risk_class") in {RiskClass.DESTRUCTIVE.value, RiskClass.LONG_RUNNING.value}:
            severity = MirrorSeverity.WARNING.value
        recovery_options = payload.get("options") if payload["interaction_kind"] == InteractionKind.RECOVERY.value else None
        return self.create_mirror_event(
            event_type=event_type,
            severity=severity,
            user_visible_summary=payload["user_visible_summary"],
            current_state_summary=f"{payload['interaction_function']} is waiting for the Client Frontend.",
            mirror_event_id=payload.get("mirror_event_id"),
            workflow_run_id=payload.get("workflow_run_id"),
            workflow_tool=payload.get("function_or_route"),
            user_visible_cause=payload.get("user_visible_cause"),
            kernel_dialog_state=dialog_state,
            recovery_options=recovery_options if isinstance(recovery_options, list) else None,
            allowed_agent_tools=allowed_agent_tools or (),
            tool_availability_expires_at=tool_availability_expires_at,
        )

    def create_passive_snapshot(
        self,
        *,
        event_type: str,
        severity: str = MirrorSeverity.INFO.value,
        user_visible_summary: str,
        current_state_summary: str,
    ) -> MirrorEvent:
        return self.create_mirror_event(
            event_type=event_type,
            severity=severity,
            user_visible_summary=user_visible_summary,
            current_state_summary=current_state_summary,
            is_kernel_auto_call=False,
            allowed_agent_tools=(),
        )

    def expire_event_scoped_tools(self, mirror_event_id: str, reason: str):
        return self.store.mark_event_scoped_tools_expired(mirror_event_id, reason)
