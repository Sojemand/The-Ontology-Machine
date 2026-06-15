from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from semantic_control_kernel.types.agent_tool_constants import (
    AGENT_TOOL_DEFINITION_SCHEMA_VERSION,
    AGENT_TOOL_HANDLER_STATUSES,
    AGENT_TOOL_LAYERS,
    AGENT_TOOL_SURFACE_INVENTORY_SCHEMA_VERSION,
    AGENT_TOOL_SURFACE_VERSION,
    AGENT_TOOL_VISIBILITIES,
)


class AgentToolContractError(ValueError):
    pass


def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(value))


def empty_model_visible_schema() -> dict[str, Any]:
    return {"type": "object", "properties": {}, "additionalProperties": False}


@dataclass(frozen=True)
class AgentToolDefinition:
    tool_name: str
    visibility: str
    layer: str
    description: str
    outcome: str
    does_not: str
    implemented_by_phase: int
    handler_status: str | None = None
    event_scoped_recovery_class: str | None = None
    schema_version: str = AGENT_TOOL_DEFINITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != AGENT_TOOL_DEFINITION_SCHEMA_VERSION:
            raise AgentToolContractError(f"Unexpected tool definition schema: {self.schema_version}")
        if self.visibility not in AGENT_TOOL_VISIBILITIES:
            raise AgentToolContractError(f"Unknown tool visibility: {self.visibility}")
        if self.layer not in AGENT_TOOL_LAYERS:
            raise AgentToolContractError(f"Unknown tool layer: {self.layer}")
        if self.handler_status is not None and self.handler_status not in AGENT_TOOL_HANDLER_STATUSES:
            raise AgentToolContractError(f"Unknown handler status: {self.handler_status}")
        for field_name in ("tool_name", "description", "outcome", "does_not"):
            if not getattr(self, field_name):
                raise AgentToolContractError(f"Agent tool definition missing {field_name}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "tool_name": self.tool_name,
            "visibility": self.visibility,
            "layer": self.layer,
            "description": self.description,
            "outcome": self.outcome,
            "does_not": self.does_not,
            "implemented_by_phase": self.implemented_by_phase,
        }
        if self.handler_status is not None:
            payload["handler_status"] = self.handler_status
        if self.event_scoped_recovery_class is not None:
            payload["event_scoped_recovery_class"] = self.event_scoped_recovery_class
        return payload


@dataclass(frozen=True)
class AgentToolSurfaceInventory:
    context_preamble: str
    permanent_tools: tuple[AgentToolDefinition, ...]
    event_scoped_recovery_tools: tuple[AgentToolDefinition, ...]
    rejected_legacy_names: tuple[str, ...]
    generated_from_spec_refs: tuple[str, ...] = ()
    surface_version: str = AGENT_TOOL_SURFACE_VERSION
    schema_version: str = AGENT_TOOL_SURFACE_INVENTORY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "surface_version": self.surface_version,
            "context_preamble": self.context_preamble,
            "permanent_tools": [tool.to_dict() for tool in self.permanent_tools],
            "event_scoped_recovery_tools": [tool.to_dict() for tool in self.event_scoped_recovery_tools],
            "rejected_legacy_names": list(self.rejected_legacy_names),
        }
        if self.generated_from_spec_refs:
            payload["generated_from_spec_refs"] = list(self.generated_from_spec_refs)
        return payload
