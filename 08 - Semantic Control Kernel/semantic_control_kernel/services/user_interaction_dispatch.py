from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.services.user_interaction_models import InteractionDispatchResult
from semantic_control_kernel.types.client_frontend_events import ClientFrontendEvent
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity
from semantic_control_kernel.types.events import UserInteractionRequest
from semantic_control_kernel.types.interaction import build_expiration_policy, validate_user_interaction_request


class InteractionDispatchMixin:
    def _persist_mirror_and_dispatch(
        self,
        request: UserInteractionRequest,
        *,
        allowed_agent_tools: Sequence[str],
    ) -> InteractionDispatchResult:
        validate_user_interaction_request(request)
        policy = request.payload["expiration_policy"]
        if isinstance(policy, Mapping) and policy.get("policy_id") != "notice_no_response":
            self.interaction_store.put_pending_interaction(request)
        mirror_event = self.mirror_event_service.create_for_interaction_request(
            request,
            allowed_agent_tools=allowed_agent_tools,
            tool_availability_expires_at=request.payload["expiration_policy"].get("expires_at")
            if isinstance(request.payload.get("expiration_policy"), Mapping)
            else None,
        )
        frontend_event = self._frontend_event(
            "interaction_request",
            mirror_event.payload["mirror_event_id"],
            interaction_request=request.to_dict(),
        )
        ack = self.event_sink.emit(frontend_event)
        workflow_waiting = False
        if not ack.payload["accepted"]:
            workflow_waiting = self._mark_workflow_waiting(request)
            self.mirror_event_service.create_mirror_event(
                event_type=MirrorEventType.BLOCKER.value,
                severity=MirrorSeverity.WARNING.value,
                user_visible_summary="Client Frontend host surface is unavailable.",
                current_state_summary="Workflow is waiting for the Client Frontend event sink.",
                workflow_run_id=request.payload["workflow_run_id"],
                workflow_tool=request.payload["function_or_route"],
                user_visible_cause="host_surface_unavailable",
                kernel_dialog_state="not_required",
                allowed_agent_tools=(),
            )
        return InteractionDispatchResult(
            request=request,
            mirror_event=mirror_event,
            frontend_event=frontend_event,
            ack=ack,
            workflow_marked_waiting=workflow_waiting,
        )

    def _base_request_payload(
        self,
        *,
        interaction_request_id: str,
        workflow_run_id: str,
        function_or_route: str,
        interaction_function: str,
        interaction_kind: str,
        dialog_type: str,
        target_identity: Mapping[str, Any],
        state_snapshot_identity: Mapping[str, Any],
        user_visible_title: str,
        user_visible_summary: str,
        response_shape: str,
        expiration_policy_id: str,
        mirror_event_id: str,
    ) -> dict[str, Any]:
        return {
            "created_at": utc_iso(),
            "dialog_type": dialog_type,
            "expiration_policy": build_expiration_policy(expiration_policy_id),
            "function_or_route": function_or_route,
            "interaction_function": interaction_function,
            "interaction_kind": interaction_kind,
            "interaction_request_id": interaction_request_id,
            "mirror_event_id": mirror_event_id,
            "response_shape": response_shape,
            "schema_version": UserInteractionRequest.SCHEMA_VERSION,
            "state_snapshot_identity": dict(state_snapshot_identity),
            "target_identity": dict(target_identity),
            "user_visible_summary": user_visible_summary,
            "user_visible_title": user_visible_title,
            "workflow_run_id": workflow_run_id,
        }

    def _frontend_event(self, kind: str, mirror_event_id: str, **payload_fields: Any) -> ClientFrontendEvent:
        payload = {
            "created_at": utc_iso(),
            "frontend_event_id": generate_id("frontend_event_id"),
            "frontend_event_kind": kind,
            "mirror_event_id": mirror_event_id,
            "schema_version": ClientFrontendEvent.SCHEMA_VERSION,
        }
        payload.update(payload_fields)
        return ClientFrontendEvent.from_dict(payload)

    def _mark_workflow_waiting(self, request: UserInteractionRequest) -> bool:
        if self.workflow_run_store is None:
            return False
        try:
            self.workflow_run_store.mark_run_waiting(
                request.payload["workflow_run_id"],
                f"pending_interactions/active/{request.payload['interaction_request_id']}.json",
            )
            return True
        except ResumeStateNotFoundError:
            return False
