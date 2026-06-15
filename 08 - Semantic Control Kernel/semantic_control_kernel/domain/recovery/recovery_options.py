from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.domain.recovery.recovery_matrix import RecoveryMatrix
from semantic_control_kernel.domain.recovery.recovery_option_specs import option_for_tool
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.types.enums import RecoveryActionType, RecoveryOwner, RecoveryStateClass, RiskClass
from semantic_control_kernel.types.recovery import RECOVERY_OPTION_SCHEMA_VERSION, RecoveryOption
from semantic_control_kernel.validation.recovery_validation import validate_recovery_option


class RecoveryOptionService:
    def __init__(self, matrix: RecoveryMatrix | None = None) -> None:
        self.matrix = matrix or RecoveryMatrix()

    def create_options(
        self,
        *,
        recovery_event_id: str,
        recovery_state: str,
        target_identity: Mapping[str, Any],
        state_snapshot_identity: Mapping[str, Any],
        expires_at: str,
        support_bundle_ref: Mapping[str, Any] | None = None,
        safe_tools: Sequence[str] | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> tuple[RecoveryOption, ...]:
        support_ref = dict(support_bundle_ref or {})
        if recovery_state == RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value:
            return (self._support_only_option(recovery_event_id, target_identity, state_snapshot_identity, expires_at, support_ref),)

        options: list[RecoveryOption] = []
        tools = tuple(safe_tools) if safe_tools is not None else self.matrix.get(recovery_state).event_scoped_agent_tools
        for tool in tools:
            option = option_for_tool(
                tool,
                recovery_state=recovery_state,
                matrix=self.matrix,
                make_option=self._option,
                base_kwargs={
                    "recovery_event_id": recovery_event_id,
                    "target_identity": target_identity,
                    "state_snapshot_identity": state_snapshot_identity,
                    "expires_at": expires_at,
                },
                support_bundle_ref=support_ref,
                evidence=dict(evidence or {}),
            )
            if option is not None:
                options.append(option)
        if not options and support_ref:
            options.append(self._fallback_support_option(recovery_event_id, target_identity, state_snapshot_identity, expires_at, support_ref))
        return tuple(options)

    def _support_only_option(
        self,
        recovery_event_id: str,
        target_identity: Mapping[str, Any],
        state_snapshot_identity: Mapping[str, Any],
        expires_at: str,
        support_bundle_ref: Mapping[str, Any],
    ) -> RecoveryOption:
        return self._option(
            recovery_event_id=recovery_event_id,
            label="Open support bundle",
            description="Open the Kernel support bundle for this terminal recovery state.",
            owner=RecoveryOwner.SUPPORT_SURFACE.value,
            recovery_action_type=RecoveryActionType.SUPPORT_ONLY.value,
            effect="support_only_terminal",
            risk_class=RiskClass.SUPPORT.value,
            target_identity=target_identity,
            state_snapshot_identity=state_snapshot_identity,
            agent_tool="kernel_open_support_bundle",
            kernel_dialog_action="support_bundle_dialog",
            expires_at=expires_at,
            support_bundle_ref=support_bundle_ref,
        )

    def _fallback_support_option(
        self,
        recovery_event_id: str,
        target_identity: Mapping[str, Any],
        state_snapshot_identity: Mapping[str, Any],
        expires_at: str,
        support_bundle_ref: Mapping[str, Any],
    ) -> RecoveryOption:
        return self._option(
            recovery_event_id=recovery_event_id,
            label="Open support bundle",
            description="Open the Kernel support bundle because no mutation recovery is safe.",
            owner=RecoveryOwner.SUPPORT_SURFACE.value,
            recovery_action_type=RecoveryActionType.OPEN_SUPPORT_BUNDLE.value,
            effect="support_bundle",
            risk_class=RiskClass.SUPPORT.value,
            target_identity=target_identity,
            state_snapshot_identity=state_snapshot_identity,
            agent_tool="kernel_open_support_bundle",
            kernel_dialog_action="support_bundle_dialog",
            expires_at=expires_at,
            support_bundle_ref=support_bundle_ref,
        )

    def _option(
        self,
        *,
        recovery_event_id: str,
        label: str,
        description: str,
        owner: str,
        recovery_action_type: str,
        effect: str,
        risk_class: str,
        target_identity: Mapping[str, Any],
        state_snapshot_identity: Mapping[str, Any],
        agent_tool: str | None = None,
        kernel_dialog_action: str | None = None,
        starts_new_workflow: bool = False,
        continuation_workflow_tool: str | None = None,
        requires_confirmation: bool = False,
        expires_at: str = "",
        support_bundle_ref: Mapping[str, Any] | None = None,
    ) -> RecoveryOption:
        payload = {
            "agent_tool": agent_tool,
            "continuation_workflow_tool": continuation_workflow_tool,
            "description": description,
            "effect": effect,
            "expires_at": expires_at,
            "kernel_dialog_action": kernel_dialog_action,
            "label": label,
            "owner": owner,
            "recovery_action_type": recovery_action_type,
            "recovery_event_id": recovery_event_id,
            "recovery_id": generate_id("recovery_id"),
            "requires_confirmation": requires_confirmation,
            "risk_class": risk_class,
            "schema_version": RECOVERY_OPTION_SCHEMA_VERSION,
            "starts_new_workflow": starts_new_workflow,
            "state_snapshot_identity": dict(state_snapshot_identity),
            "target_identity": dict(target_identity),
        }
        validate_recovery_option(payload)
        return RecoveryOption(payload)
