from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.services.user_interaction_models import InteractionDispatchResult
from semantic_control_kernel.services.user_interaction_safety import safe_recovery_option, safe_support_text
from semantic_control_kernel.types.enums import DialogType, InteractionKind, RecoveryDialogType
from semantic_control_kernel.types.events import UserInteractionRequest
from semantic_control_kernel.types.interaction import RECOVERY_DIALOG_MAPPINGS, USER_INTERACTION_MAPPINGS
from semantic_control_kernel.validation.contract_validation import KernelContractError


class InteractionRequestMixin:
    def request_interaction(
        self,
        *,
        interaction_function: str,
        workflow_run_id: str,
        function_or_route: str,
        target_identity: Mapping[str, Any],
        state_snapshot_identity: Mapping[str, Any],
        user_visible_title: str,
        user_visible_summary: str,
        risk_class: str | None = None,
        options: Sequence[Mapping[str, Any]] | None = None,
        prefilled_values: Mapping[str, Any] | None = None,
        confirmation_request_id: str | None = None,
        expiration_policy_id: str | None = None,
        allowed_agent_tools: Sequence[str] | None = None,
    ) -> InteractionDispatchResult:
        if allowed_agent_tools:
            raise KernelContractError("Non-recovery user interactions must not expose event-scoped Agent tools.")
        mapping = USER_INTERACTION_MAPPINGS[interaction_function]
        payload = self._base_request_payload(
            interaction_request_id=generate_id("interaction_request_id"),
            workflow_run_id=workflow_run_id,
            function_or_route=function_or_route,
            interaction_function=interaction_function,
            interaction_kind=mapping.interaction_kind,
            dialog_type=mapping.dialog_type,
            target_identity=target_identity,
            state_snapshot_identity=state_snapshot_identity,
            user_visible_title=user_visible_title,
            user_visible_summary=user_visible_summary,
            response_shape=mapping.response_shape,
            expiration_policy_id=expiration_policy_id or mapping.expiration_policy_id,
            mirror_event_id=generate_id("mirror_event_id"),
        )
        if risk_class is not None:
            payload["risk_class"] = risk_class
        if options is not None:
            payload["options"] = [dict(option) for option in options]
        if prefilled_values is not None:
            payload["prefilled_values"] = dict(prefilled_values)
        if confirmation_request_id is not None:
            payload["confirmation_request_id"] = confirmation_request_id
        request = UserInteractionRequest.from_dict(payload)
        return self._persist_mirror_and_dispatch(request, allowed_agent_tools=allowed_agent_tools or ())

    def request_recovery_dialog(
        self,
        *,
        recovery_dialog_type: str,
        recovery_id: str,
        workflow_run_id: str,
        function_or_route: str,
        target_identity: Mapping[str, Any],
        state_snapshot_identity: Mapping[str, Any],
        user_visible_title: str,
        user_visible_summary: str,
        user_visible_cause: str,
        recovery_effect: str,
        risk_class: str,
        options: Sequence[Mapping[str, Any]] | None = None,
        allowed_agent_tools: Sequence[str] | None = None,
    ) -> InteractionDispatchResult:
        if recovery_dialog_type not in RECOVERY_DIALOG_MAPPINGS:
            raise ValueError(f"Unknown recovery dialog type: {recovery_dialog_type}")
        if recovery_dialog_type == RecoveryDialogType.SUPPORT_BUNDLE_DIALOG.value:
            user_visible_title = safe_support_text(user_visible_title)
            user_visible_summary = safe_support_text(user_visible_summary)
            user_visible_cause = safe_support_text(user_visible_cause)
            recovery_effect = safe_support_text(recovery_effect)
        payload = self._base_request_payload(
            interaction_request_id=generate_id("interaction_request_id"),
            workflow_run_id=workflow_run_id,
            function_or_route=function_or_route,
            interaction_function="kernel_recovery_dialog",
            interaction_kind=InteractionKind.RECOVERY.value,
            dialog_type=DialogType.RECOVERY_DIALOG.value,
            target_identity=target_identity,
            state_snapshot_identity=state_snapshot_identity,
            user_visible_title=user_visible_title,
            user_visible_summary=user_visible_summary,
            response_shape="recovery_dialog_response",
            expiration_policy_id="recovery_event_scoped",
            mirror_event_id=generate_id("mirror_event_id"),
        )
        payload.update(
            {
                "options": [safe_recovery_option(option) for option in options or ()],
                "prefilled_values": {
                    "recovery_effect": recovery_effect,
                    "user_visible_cause": user_visible_cause,
                },
                "recovery_dialog_type": recovery_dialog_type,
                "recovery_id": recovery_id,
                "risk_class": risk_class,
            }
        )
        request = UserInteractionRequest.from_dict(payload)
        return self._persist_mirror_and_dispatch(request, allowed_agent_tools=allowed_agent_tools or ())
