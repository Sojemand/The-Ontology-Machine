from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_NAMES
from semantic_control_kernel.types.enums import (
    MirrorEventType,
    RecoveryActionType,
    RecoveryOwner,
    RecoveryResultStatus,
    RecoveryStateClass,
    RiskClass,
)
from semantic_control_kernel.types.recovery import (
    RECOVERY_EVENT_SCHEMA_VERSION,
    RECOVERY_OPTION_SCHEMA_VERSION,
    RECOVERY_RECEIPT_SCHEMA_VERSION,
    SUPPORT_BUNDLE_REF_SCHEMA_VERSION,
)
from semantic_control_kernel.validation.contract_validation import EnumValidationError, KernelContractError, UnknownFieldError
from semantic_control_kernel.validation.recovery_validation_bindings import (
    validate_allowed_tools_against_options,
    validate_recovery_event_option_bindings,
)
from semantic_control_kernel.validation.recovery_validation_helpers import (
    reject_agent_authored_domain_payloads,
    validate_allowed_tools,
    validate_closed_payload,
    validate_enum,
)
from semantic_control_kernel.validation.recovery_validation_schema import (
    RECOVERY_EVENT_REQUIRED_FIELDS,
    RECOVERY_EVENT_STATUSES,
    RECOVERY_OPTION_REQUIRED_FIELDS,
    RECOVERY_RECEIPT_REQUIRED_FIELDS,
    RECOVERY_TOOL_INPUT_FIELDS,
    RECOVERY_TOOL_OUTPUT_FIELDS,
    SUPPORT_BUNDLE_REF_REQUIRED_FIELDS,
)


def validate_recovery_event(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(payload, RECOVERY_EVENT_SCHEMA_VERSION, RECOVERY_EVENT_REQUIRED_FIELDS)
    validate_enum(payload["recovery_state"], RecoveryStateClass, "kernel.recovery_event.v1.recovery_state")
    validate_enum(payload["status"], RECOVERY_EVENT_STATUSES, "kernel.recovery_event.v1.status")
    if not isinstance(payload["recovery_options"], list):
        raise KernelContractError("kernel.recovery_event.v1.recovery_options must be a list.")
    if not isinstance(payload["allowed_agent_tools"], list):
        raise KernelContractError("kernel.recovery_event.v1.allowed_agent_tools must be a list.")
    for option in payload["recovery_options"]:
        if not isinstance(option, Mapping):
            raise KernelContractError("kernel.recovery_event.v1.recovery_options items must be objects.")
        validate_recovery_option(option)
    validate_allowed_tools(payload["allowed_agent_tools"], "kernel.recovery_event.v1.allowed_agent_tools")
    validate_recovery_event_option_bindings(payload)


def validate_recovery_option(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(payload, RECOVERY_OPTION_SCHEMA_VERSION, RECOVERY_OPTION_REQUIRED_FIELDS)
    validate_enum(payload["owner"], RecoveryOwner, "kernel.recovery_option.v1.owner")
    validate_enum(payload["recovery_action_type"], RecoveryActionType, "kernel.recovery_option.v1.recovery_action_type")
    validate_enum(payload["risk_class"], RiskClass, "kernel.recovery_option.v1.risk_class")
    _validate_agent_tool(payload.get("agent_tool"))
    for key in ("starts_new_workflow", "requires_confirmation"):
        if not isinstance(payload[key], bool):
            raise KernelContractError(f"kernel.recovery_option.v1.{key} must be boolean.")


def validate_recovery_receipt(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(payload, RECOVERY_RECEIPT_SCHEMA_VERSION, RECOVERY_RECEIPT_REQUIRED_FIELDS)
    validate_enum(payload["recovery_state"], RecoveryStateClass, "kernel.recovery_receipt.v1.recovery_state")
    validate_enum(payload["result_status"], RecoveryResultStatus, "kernel.recovery_receipt.v1.result_status")
    for list_key in ("written_refs", "mutated_refs", "user_confirmation_refs"):
        if not isinstance(payload[list_key], list):
            raise KernelContractError(f"kernel.recovery_receipt.v1.{list_key} must be a list.")


def validate_support_bundle_ref(payload: Mapping[str, Any]) -> None:
    validate_closed_payload(payload, SUPPORT_BUNDLE_REF_SCHEMA_VERSION, SUPPORT_BUNDLE_REF_REQUIRED_FIELDS)
    if not isinstance(payload["included_refs"], list):
        raise KernelContractError("kernel.support_bundle_ref.v1.included_refs must be a list.")
    if not isinstance(payload["redaction_profile"], Mapping):
        raise KernelContractError("kernel.support_bundle_ref.v1.redaction_profile must be an object.")


def validate_recovery_tool_input(tool_name: str, payload: Mapping[str, Any]) -> None:
    fields = RECOVERY_TOOL_INPUT_FIELDS.get(tool_name)
    if fields is None:
        raise UnknownFieldError(f"Unknown recovery tool: {tool_name}")
    validate_closed_payload(payload, str(payload.get("schema_version", "")), fields, allow_any_schema=True)
    reject_agent_authored_domain_payloads(payload, f"{tool_name}.input")


def validate_recovery_tool_output(tool_name: str, payload: Mapping[str, Any]) -> None:
    fields = RECOVERY_TOOL_OUTPUT_FIELDS.get(tool_name)
    if fields is None:
        raise UnknownFieldError(f"Unknown recovery tool: {tool_name}")
    validate_closed_payload(payload, str(payload.get("schema_version", "")), fields, allow_any_schema=True)
    support_bundle_ref = payload.get("support_bundle_ref")
    if support_bundle_ref is not None:
        if not isinstance(support_bundle_ref, Mapping):
            raise KernelContractError(f"{tool_name}.support_bundle_ref must be an object when present.")
        validate_support_bundle_ref(support_bundle_ref)


def assert_recovery_mirror_event(payload: Mapping[str, Any]) -> None:
    if payload.get("mirror_source") != "kernel":
        raise KernelContractError("Recovery mirror event must be Kernel-authored.")
    if payload.get("is_kernel_auto_call") is not True:
        raise KernelContractError("Recovery mirror event must be a Kernel auto-call.")
    validate_enum(
        payload.get("event_type"),
        (
            MirrorEventType.RECOVERY_STATE.value,
            MirrorEventType.VALIDATION_ERROR.value,
            MirrorEventType.PIPELINE_ERROR.value,
            MirrorEventType.LLM_VALIDATION_FAILED_FINAL.value,
            MirrorEventType.BLOCKER.value,
        ),
        "kernel.mirror_event.v1.event_type",
    )
    validate_allowed_tools(payload.get("allowed_agent_tools", []), "kernel.mirror_event.v1.allowed_agent_tools")
    recovery_options = payload.get("recovery_options", []) or []
    if not isinstance(recovery_options, list):
        raise KernelContractError("kernel.mirror_event.v1.recovery_options must be a list when present.")
    for option in recovery_options:
        if not isinstance(option, Mapping):
            raise KernelContractError("kernel.mirror_event.v1.recovery_options items must be objects.")
        validate_recovery_option(option)
    validate_allowed_tools_against_options(
        payload.get("allowed_agent_tools", []),
        recovery_options,
        "kernel.mirror_event.v1.allowed_agent_tools",
    )


def _validate_agent_tool(agent_tool: Any) -> None:
    always_visible = {
        "kernel_status",
        "kernel_resume_state",
        "kernel_cancel_active_run",
        "create_custom_taxonomy_path",
        "create_custom_projection_path",
    }
    if agent_tool is not None and agent_tool not in EVENT_SCOPED_RECOVERY_TOOL_NAMES and agent_tool not in always_visible:
        raise EnumValidationError(f"kernel.recovery_option.v1.agent_tool is not a known event-scoped tool: {agent_tool!r}.")
