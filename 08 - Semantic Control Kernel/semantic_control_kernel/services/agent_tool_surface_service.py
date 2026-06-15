from __future__ import annotations

from datetime import datetime, timezone

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.surface.agent_tools import (
    AGENT_SURFACE_CONTEXT_PREAMBLE,
    GENERATED_FROM_SPEC_REFS,
    PERMANENT_AGENT_TOOL_DEFINITIONS,
)
from semantic_control_kernel.surface.event_scoped_tools import (
    EVENT_SCOPED_RECOVERY_TOOL_MAP,
    list_event_scoped_recovery_tool_definitions,
)
from semantic_control_kernel.types.agent_tools import (
    AgentToolDefinition,
    AgentToolSurfaceInventory,
    REJECTED_LEGACY_AGENT_SURFACE_NAMES,
)
from semantic_control_kernel.validation.contract_validation import KernelContractError
from semantic_control_kernel.validation.recovery_validation import assert_recovery_mirror_event


class AgentToolSurfaceService:
    def __init__(self, mirror_event_store: MirrorEventStore | None = None) -> None:
        self.mirror_event_store = mirror_event_store

    def list_permanent_tools(self) -> tuple[AgentToolDefinition, ...]:
        return PERMANENT_AGENT_TOOL_DEFINITIONS

    def list_defined_event_scoped_recovery_tools(self) -> tuple[AgentToolDefinition, ...]:
        return list_event_scoped_recovery_tool_definitions()

    def list_event_scoped_tools(self, mirror_event_id: str | None) -> tuple[AgentToolDefinition, ...]:
        if not mirror_event_id or self.mirror_event_store is None:
            return ()
        try:
            mirror_event = self.mirror_event_store.get_mirror_event(mirror_event_id)
            availability = self.mirror_event_store.get_tool_availability(mirror_event_id)
        except ResumeStateNotFoundError:
            return ()
        mirror_payload = mirror_event.to_dict()
        try:
            assert_recovery_mirror_event(mirror_payload)
        except KernelContractError:
            return ()
        payload = availability.to_dict()
        if payload.get("status") != "active" or _is_expired(payload.get("expires_at")):
            return ()
        mirror_allowed = {
            tool_name
            for tool_name in mirror_payload.get("allowed_agent_tools", [])
            if isinstance(tool_name, str)
        }
        tools: list[AgentToolDefinition] = []
        seen: set[str] = set()
        for tool_name in payload.get("allowed_agent_tools", []):
            if not isinstance(tool_name, str):
                continue
            if tool_name not in mirror_allowed:
                continue
            if tool_name in seen:
                continue
            tool = EVENT_SCOPED_RECOVERY_TOOL_MAP.get(tool_name)
            if tool is not None:
                tools.append(tool)
                seen.add(tool_name)
        return tuple(tools)

    def build_inventory(self, mirror_event_id: str | None = None) -> AgentToolSurfaceInventory:
        return AgentToolSurfaceInventory(
            context_preamble=AGENT_SURFACE_CONTEXT_PREAMBLE,
            permanent_tools=self.list_permanent_tools(),
            event_scoped_recovery_tools=self.list_event_scoped_tools(mirror_event_id),
            rejected_legacy_names=REJECTED_LEGACY_AGENT_SURFACE_NAMES,
            generated_from_spec_refs=GENERATED_FROM_SPEC_REFS,
        )


def _is_expired(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return True
    try:
        expires_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    return expires_at <= datetime.now(timezone.utc)
