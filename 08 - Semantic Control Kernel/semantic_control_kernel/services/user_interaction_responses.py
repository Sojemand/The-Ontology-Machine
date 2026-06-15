from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import stable_hash, utc_iso
from semantic_control_kernel.services.user_interaction_models import InteractionResponseResult
from semantic_control_kernel.services.user_interaction_response_state import response_mismatch_state
from semantic_control_kernel.types.enums import InteractionKind, InteractionResponseStatus, MirrorEventType, MirrorSeverity
from semantic_control_kernel.types.events import UserInteractionResponse
from semantic_control_kernel.types.interaction import (
    validate_user_interaction_response,
    validate_user_interaction_response_for_request,
)
from semantic_control_kernel.types.receipts import ConfirmationReceipt


class InteractionResponseMixin:
    def submit_response(
        self,
        response: UserInteractionResponse,
        *,
        now_utc: datetime | None = None,
    ) -> InteractionResponseResult:
        validate_user_interaction_response(response)
        payload = response.to_dict()
        request = self.interaction_store.get_pending_interaction(payload["interaction_request_id"])
        request_payload = request.to_dict()
        mismatch_state = response_mismatch_state(request_payload, payload, now_utc=now_utc)
        if mismatch_state is None:
            mismatch_state = self._workflow_mismatch_state(request_payload)
        if mismatch_state is None and request_payload.get("recovery_id") is not None:
            if payload.get("recovery_id") != request_payload["recovery_id"]:
                mismatch_state = "target_identity_changed"
        if mismatch_state is not None:
            return self._reject_response(response, request_payload, mismatch_state)
        validate_user_interaction_response_for_request(request_payload, payload)
        status = payload["response_status"]
        if status != InteractionResponseStatus.SUBMITTED.value:
            self._finalize_terminal_response(payload)
            self._expire_event_scoped_tools_for_request(request_payload, status)
            return InteractionResponseResult(
                response=response,
                accepted=True,
                consumed_value=False,
                terminal_status=status,
            )
        self.interaction_store.submit_interaction_response(response, now_utc=now_utc)
        self._expire_event_scoped_tools_for_request(request_payload, "resolved")
        receipt = None
        if request_payload["interaction_kind"] == InteractionKind.CONFIRMATION.value:
            receipt = self._append_confirmation_receipt(request_payload, payload)
        return InteractionResponseResult(
            response=response,
            accepted=True,
            consumed_value=True,
            terminal_status=status,
            confirmation_receipt=receipt,
        )

    def _finalize_terminal_response(self, payload: Mapping[str, Any]) -> None:
        request_id = str(payload["interaction_request_id"])
        reason = str(payload.get("cancellation_reason", payload["response_status"]))
        status = str(payload["response_status"])
        if status == InteractionResponseStatus.CANCELLED.value:
            self.interaction_store.cancel_interaction(request_id, reason)
        elif status == InteractionResponseStatus.CLOSED.value:
            self.interaction_store.close_interaction(request_id, reason)
        elif status == InteractionResponseStatus.EXPIRED.value:
            self.interaction_store.expire_interaction(request_id, reason)
        elif status == InteractionResponseStatus.SUPERSEDED.value:
            self.interaction_store.supersede_interaction(request_id)
        elif status == InteractionResponseStatus.REJECTED_STALE.value:
            self.interaction_store.reject_stale_interaction(request_id, reason)

    def _workflow_mismatch_state(self, request_payload: Mapping[str, Any]) -> str | None:
        if self.workflow_run_store is None:
            return None
        workflow_run_id = str(request_payload["workflow_run_id"])
        try:
            workflow_run = self.workflow_run_store.get_run(workflow_run_id)
        except ResumeStateNotFoundError:
            return "superseded_workflow_run"
        if workflow_run.status not in {"running", "waiting"}:
            return "superseded_workflow_run"
        if dict(workflow_run.target_identity) != dict(request_payload["target_identity"]):
            return "target_identity_changed"
        return None

    def _expire_event_scoped_tools_for_request(self, request_payload: Mapping[str, Any], reason: str) -> None:
        if request_payload.get("interaction_kind") != InteractionKind.RECOVERY.value:
            return
        mirror_event_id = request_payload.get("mirror_event_id")
        if not isinstance(mirror_event_id, str) or not mirror_event_id:
            return
        try:
            self.mirror_event_service.expire_event_scoped_tools(mirror_event_id, reason)
        except ResumeStateNotFoundError:
            return

    def _reject_response(
        self,
        response: UserInteractionResponse,
        request_payload: Mapping[str, Any],
        recovery_state: str,
    ) -> InteractionResponseResult:
        request_id = response.payload["interaction_request_id"]
        if recovery_state == "expired_pending_interaction":
            self.interaction_store.expire_interaction(request_id, "timeout")
            terminal_status = InteractionResponseStatus.EXPIRED.value
        elif recovery_state == "superseded_workflow_run":
            self.interaction_store.supersede_interaction(request_id)
            terminal_status = InteractionResponseStatus.SUPERSEDED.value
        else:
            self.interaction_store.reject_stale_interaction(request_id, recovery_state)
            terminal_status = InteractionResponseStatus.REJECTED_STALE.value
        self._expire_event_scoped_tools_for_request(request_payload, recovery_state)
        self.interaction_store.record_stale_response_ref(
            request_id,
            {
                "interaction_response_id": response.payload["interaction_response_id"],
                "recovery_state": recovery_state,
                "recorded_at": utc_iso(),
            },
        )
        mirror_event = self.mirror_event_service.create_mirror_event(
            event_type=MirrorEventType.RECOVERY_STATE.value,
            severity=MirrorSeverity.RECOVERABLE_ERROR.value,
            user_visible_summary=f"Interaction response rejected: {recovery_state}.",
            current_state_summary="The stale value was not consumed by the Kernel.",
            workflow_run_id=request_payload.get("workflow_run_id"),
            workflow_tool=request_payload.get("function_or_route"),
            user_visible_cause=recovery_state,
            kernel_dialog_state="not_required",
            allowed_agent_tools=(),
        )
        return InteractionResponseResult(
            response=response,
            accepted=False,
            consumed_value=False,
            terminal_status=terminal_status,
            recovery_state=recovery_state,
            mirror_event=mirror_event,
        )

    def _append_confirmation_receipt(
        self,
        request_payload: Mapping[str, Any],
        response_payload: Mapping[str, Any],
    ) -> ConfirmationReceipt:
        receipt_payload = {
            "confirmation_receipt_id": generate_id("confirmation_receipt_id"),
            "confirmation_request_id": request_payload.get("confirmation_request_id")
            or request_payload["interaction_request_id"],
            "confirmed_at": response_payload["submitted_at"],
            "confirmed_state_snapshot_identity": response_payload["state_snapshot_identity"],
            "confirmed_target_identity": response_payload["target_identity"],
            "explanation_hash": stable_hash(
                f"{request_payload['user_visible_title']}::{request_payload['user_visible_summary']}"
            ),
            "host_surface_identity": response_payload["host_surface_identity"],
            "schema_version": ConfirmationReceipt.SCHEMA_VERSION,
            "user_decision": response_payload["confirmation_decision"],
        }
        receipt = ConfirmationReceipt.from_dict(receipt_payload)
        if self.receipt_store is not None:
            self.receipt_store.append_confirmation_receipt(receipt)
        return receipt
