from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.validation.contract_validation import KernelContractError


def validate_recovery_event_option_bindings(payload: Mapping[str, Any]) -> None:
    for index, option in enumerate(payload["recovery_options"]):
        option_prefix = f"kernel.recovery_event.v1.recovery_options[{index}]"
        if option["recovery_event_id"] != payload["recovery_event_id"]:
            raise KernelContractError(f"{option_prefix}.recovery_event_id must match kernel.recovery_event.v1.recovery_event_id.")
        if option["target_identity"] != payload["target_identity"]:
            raise KernelContractError(f"{option_prefix}.target_identity must match kernel.recovery_event.v1.target_identity.")
        if option["state_snapshot_identity"] != payload["state_snapshot_identity"]:
            raise KernelContractError(f"{option_prefix}.state_snapshot_identity must match kernel.recovery_event.v1.state_snapshot_identity.")
    validate_allowed_tools_against_options(
        payload["allowed_agent_tools"],
        payload["recovery_options"],
        "kernel.recovery_event.v1.allowed_agent_tools",
    )


def validate_allowed_tools_against_options(
    allowed_agent_tools: Any,
    recovery_options: list[Mapping[str, Any]],
    field_path: str,
) -> None:
    if not isinstance(allowed_agent_tools, list):
        raise KernelContractError(f"{field_path} must be a list.")
    if not allowed_agent_tools:
        return
    option_tools = {
        str(option.get("agent_tool"))
        for option in recovery_options
        if isinstance(option.get("agent_tool"), str) and option.get("agent_tool")
    }
    if not option_tools:
        raise KernelContractError(f"{field_path} requires Kernel-authored recovery_options binding each exposed tool.")
    missing = [tool for tool in allowed_agent_tools if tool not in option_tools]
    if missing:
        raise KernelContractError(f"{field_path} includes tool(s) not bound by recovery_options: {', '.join(missing)}")
