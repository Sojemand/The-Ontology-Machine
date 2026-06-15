from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.agent_tool_workflow_dispatch import continue_workflow_after_interaction
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.surface.background_continuation import launch_interaction_continuation
from semantic_control_kernel.surface.client_frontend_continuation import (
    append_background_continuation_progress,
    mark_workflow_running,
    should_continue_inline,
)
from semantic_control_kernel.types.client_frontend_bridge import HOST_BRIDGE_RESPONSE_SCHEMA_VERSION
from semantic_control_kernel.types.events import ClientFrontendEvent, UserInteractionResponse
from semantic_control_kernel.validation.client_frontend_bridge_validation import (
    validate_host_bridge_response,
    validate_interaction_cancel_request,
    validate_interaction_response_submit_request,
)


@dataclass
class _NullEventSink:
    host_surface_identity: str = "semantic_control_kernel.host_bridge"

    def emit(self, event: ClientFrontendEvent) -> Any:
        return type(
            "_Ack",
            (),
            {
                "payload": {
                    "accepted": True,
                    "acknowledged_at": utc_iso(),
                    "frontend_event_id": event.payload["frontend_event_id"],
                    "host_surface_identity": self.host_surface_identity,
                    "schema_version": "kernel.client_frontend_event_ack.v1",
                }
            },
        )()


def submit_user_interaction_response(
    request: Mapping[str, Any],
    *,
    state_paths: StatePaths,
    continue_inline: bool | None = True,
    background_launcher: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    request = _normalized_interaction_submit_request(request)
    validate_interaction_response_submit_request(request)
    response_payload = dict(request["response"])
    response_payload.setdefault("schema_version", UserInteractionResponse.SCHEMA_VERSION)
    response_payload.setdefault("interaction_request_id", request["interaction_request_id"])
    response_payload.setdefault("target_identity", dict(request["target_identity"]))
    response_payload.setdefault("state_snapshot_identity", dict(request["state_snapshot_identity"]))
    response_payload.setdefault("host_surface_identity", request["host_surface_identity"])
    response_payload.setdefault("submitted_at", utc_iso())
    interaction_store = InteractionRequestStore(state_paths)
    pending_request = interaction_store.get_pending_interaction(request["interaction_request_id"]).to_dict()
    service = _interaction_service(state_paths)
    result = service.submit_response(UserInteractionResponse.from_dict(response_payload))
    continued = None
    continuation_ref = None
    if result.accepted and result.consumed_value:
        workflow_run_id = str(pending_request["workflow_run_id"])
        workflow_tool = str(pending_request["function_or_route"])
        if should_continue_inline(pending_request, continue_inline):
            continued = continue_workflow_after_interaction(
                workflow_run_id=workflow_run_id,
                workflow_tool=workflow_tool,
                state_paths=state_paths,
            )
        else:
            mark_workflow_running(state_paths, workflow_run_id)
            append_background_continuation_progress(
                state_paths,
                workflow_run_id=workflow_run_id,
                workflow_tool=workflow_tool,
            )
            launcher = background_launcher or launch_interaction_continuation
            continuation_ref = dict(
                launcher(
                    state_paths=state_paths,
                    workflow_run_id=workflow_run_id,
                    workflow_tool=workflow_tool,
                )
            )
    summary = "The Kernel processed the user interaction response."
    if continued is not None:
        summary = continued.user_visible_summary
    elif continuation_ref is not None:
        summary = "The Kernel accepted the user interaction response and continued the workflow in the background. Progress is available through the Client Frontend event bridge."
    payload = {
        "schema_version": HOST_BRIDGE_RESPONSE_SCHEMA_VERSION,
        "status": "accepted" if result.accepted else "rejected_stale",
        "interaction_request_id": request["interaction_request_id"],
        "user_visible_summary": summary,
        "persisted_response": result.response.to_dict(),
    }
    if continued is not None:
        payload["continued_workflow_result"] = continued.to_dict()
    if continuation_ref is not None:
        payload["background_continuation"] = continuation_ref
    if result.recovery_state is not None:
        payload["error"] = {
            "code": result.recovery_state,
            "safe_message": "The submitted response did not match the current Kernel interaction state.",
        }
    validate_host_bridge_response(payload)
    return payload


def _normalized_interaction_submit_request(request: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(request)
    response = payload.get("response")
    if isinstance(response, Mapping):
        response_payload = dict(response)
        if response_payload.get("confirmation_decision") == "declined":
            response_payload["confirmation_decision"] = "rejected"
        payload["response"] = response_payload
    return payload


def cancel_user_interaction(
    request: Mapping[str, Any],
    *,
    state_paths: StatePaths,
) -> dict[str, Any]:
    validate_interaction_cancel_request(request)
    response_status = str(request["response_status"])
    cancellation_reason = request.get("cancellation_reason")
    if not cancellation_reason:
        cancellation_reason = {
            "closed": "user_closed_dialog",
            "expired": "timeout",
        }.get(response_status, "user_cancelled")
    response_payload = {
        "schema_version": UserInteractionResponse.SCHEMA_VERSION,
        "interaction_response_id": f"cancel_{request['interaction_request_id']}",
        "interaction_request_id": request["interaction_request_id"],
        "response_status": response_status,
        "target_identity": dict(request["target_identity"]),
        "state_snapshot_identity": dict(request["state_snapshot_identity"]),
        "host_surface_identity": request["host_surface_identity"],
        "submitted_at": utc_iso(),
        "cancellation_reason": cancellation_reason,
    }
    service = _interaction_service(state_paths)
    result = service.submit_response(UserInteractionResponse.from_dict(response_payload))
    status = response_status if result.accepted else "rejected_stale"
    payload = {
        "schema_version": HOST_BRIDGE_RESPONSE_SCHEMA_VERSION,
        "status": status,
        "interaction_request_id": request["interaction_request_id"],
        "user_visible_summary": "The Kernel recorded the interaction cancellation."
        if result.accepted
        else "The Kernel rejected the stale interaction cancellation.",
        "persisted_response": result.response.to_dict(),
    }
    if result.recovery_state is not None:
        payload["error"] = {
            "code": result.recovery_state,
            "safe_message": "The cancellation did not match the current Kernel interaction state.",
        }
    validate_host_bridge_response(payload)
    return payload


def _interaction_service(state_paths: StatePaths) -> KernelUserInteractionService:
    return KernelUserInteractionService(
        interaction_store=InteractionRequestStore(state_paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(state_paths)),
        event_sink=_NullEventSink(),
        workflow_run_store=WorkflowRunStore(state_paths),
        receipt_store=ReceiptStore(state_paths),
    )
