from __future__ import annotations

from typing import Sequence

from semantic_control_kernel.types.enums import ClientFrontendEventKind, MirrorEventType, MirrorSeverity
from semantic_control_kernel.types.events import MirrorEvent, ProgressEvent
from semantic_control_kernel.validation.contract_validation import serialize_contract


class InteractionEventMixin:
    def emit_mirror_notice(
        self,
        *,
        event_type: str,
        severity: str,
        user_visible_summary: str,
        current_state_summary: str,
        workflow_run_id: str | None = None,
        workflow_tool: str | None = None,
        user_visible_cause: str | None = None,
        allowed_agent_tools: Sequence[str] | None = None,
    ):
        mirror_event = self.mirror_event_service.create_mirror_event(
            event_type=event_type,
            severity=severity,
            user_visible_summary=user_visible_summary,
            current_state_summary=current_state_summary,
            workflow_run_id=workflow_run_id,
            workflow_tool=workflow_tool,
            user_visible_cause=user_visible_cause,
            kernel_dialog_state="not_required",
            allowed_agent_tools=allowed_agent_tools or (),
        )
        frontend_event = self._frontend_event(
            ClientFrontendEventKind.MIRROR_EVENT.value,
            mirror_event.payload["mirror_event_id"],
            mirror_event=mirror_event.to_dict(),
        )
        return mirror_event, frontend_event, self.event_sink.emit(frontend_event)

    def emit_progress_event(self, progress_event: ProgressEvent):
        progress_payload = serialize_contract(progress_event)
        mirror_event = self.mirror_event_service.create_mirror_event(
            event_type=MirrorEventType.PROGRESS.value,
            severity=MirrorSeverity.INFO.value,
            user_visible_summary=progress_payload["user_visible_summary"],
            current_state_summary=progress_payload["current_state_summary"],
            workflow_run_id=progress_payload["workflow_run_id"],
            workflow_tool=progress_payload["workflow_tool"],
            kernel_dialog_state="not_required",
            progress_event=progress_event,
        )
        frontend_event = self._frontend_event(
            ClientFrontendEventKind.PROGRESS_EVENT.value,
            mirror_event.payload["mirror_event_id"],
            progress_event=progress_payload,
        )
        return mirror_event, frontend_event, self.event_sink.emit(frontend_event)
