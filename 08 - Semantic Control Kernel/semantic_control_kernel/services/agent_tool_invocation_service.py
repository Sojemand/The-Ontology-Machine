from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.agent_tool_invocation_policy import (
    is_event_scoped_recovery_tool_name,
    is_permanent_agent_tool_name,
    is_rejected_legacy_agent_surface_name,
    rejected_fields,
    string_or_none,
)
from semantic_control_kernel.services.agent_tool_invocation_state import snapshot_state_files, stable_json_text
from semantic_control_kernel.services.agent_tool_support_control import AgentToolSupportControlMixin
from semantic_control_kernel.services.agent_tool_surface_service import AgentToolSurfaceService
from semantic_control_kernel.services.agent_tool_workflow_dispatch import dispatch_permanent_workflow_tool
from semantic_control_kernel.services.resume_options import RESUME_CONTINUE_TOOL_NAME
from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_MAP
from semantic_control_kernel.types.agent_tools import AgentToolInvocation, AgentToolResult, blocked_result, rejected_result


class AgentToolInvocationService(AgentToolSupportControlMixin):
    def __init__(
        self,
        *,
        surface_service: AgentToolSurfaceService | None = None,
        state_paths: StatePaths | None = None,
        workflow_run_store: WorkflowRunStore | None = None,
        resume_store: WorkflowResumeStore | None = None,
        interaction_store: InteractionRequestStore | None = None,
    ) -> None:
        if surface_service is None and state_paths is not None:
            surface_service = AgentToolSurfaceService(MirrorEventStore(state_paths))
        self.surface_service = surface_service or AgentToolSurfaceService()
        self.state_paths = state_paths
        self.workflow_run_store = workflow_run_store or (WorkflowRunStore(state_paths) if state_paths is not None else None)
        self.resume_store = resume_store or (WorkflowResumeStore(state_paths) if state_paths is not None else None)
        self.interaction_store = interaction_store or (InteractionRequestStore(state_paths) if state_paths is not None else None)

    def invoke(
        self,
        tool_name: str,
        invocation_context: Mapping[str, Any] | None = None,
        model_payload: Mapping[str, Any] | None = None,
    ) -> AgentToolResult:
        context = dict(invocation_context or {})
        model_values = dict(model_payload or {})
        early_rejection = _early_rejection(tool_name)
        if early_rejection is not None:
            return early_rejection
        definition = PERMANENT_AGENT_TOOL_MAP.get(tool_name)
        if definition is None:
            return rejected_result(tool_name, "unknown_action", f"Unknown Semantic Control Kernel Agent tool: {tool_name}")
        rejected = rejected_fields(tool_name, context, model_values)
        if rejected:
            return _rejected_payload(tool_name, context, rejected)
        invocation = AgentToolInvocation.from_values(
            tool_name=tool_name,
            invocation_context=context,
            model_payload_status="empty" if not model_values else "client_context_only",
            client_request_id=string_or_none(context.get("client_request_id")),
            user_request_ref=string_or_none(context.get("user_request_ref")),
        )
        if definition.layer != "support_control":
            return self._dispatch_workflow_tool(tool_name, definition.implemented_by_phase)
        return self._invoke_support_control(invocation, model_values)

    def _dispatch_workflow_tool(self, tool_name: str, implemented_by_phase: str | None) -> AgentToolResult:
        if self.state_paths is None:
            return blocked_result(
                tool_name,
                code="kernel_state_unavailable",
                message="The Agent-facing workflow surface requires a resolved Kernel state root before it can dispatch the selected tool.",
                implemented_by_phase=implemented_by_phase,
            )
        return dispatch_permanent_workflow_tool(tool_name, state_paths=self.state_paths)

    def _invoke_support_control(self, invocation: AgentToolInvocation, model_values: Mapping[str, Any]) -> AgentToolResult:
        if invocation.tool_name == "kernel_status":
            return self._kernel_status(invocation)
        if invocation.tool_name == "kernel_resume_state":
            return self._kernel_resume_state(invocation)
        if invocation.tool_name == "kernel_cancel_active_run":
            return self._kernel_cancel_active_run(invocation)
        if invocation.tool_name == RESUME_CONTINUE_TOOL_NAME:
            return self._kernel_continue_resumable_workflow(invocation, model_values)
        return rejected_result(invocation.tool_name, "unknown_action", f"Unknown Semantic Control Kernel Agent tool: {invocation.tool_name}")


def invoke_agent_tool(
    tool_name: str,
    invocation_context: Mapping[str, Any] | None = None,
    model_payload: Mapping[str, Any] | None = None,
    *,
    service: AgentToolInvocationService | None = None,
) -> AgentToolResult:
    return (service or AgentToolInvocationService()).invoke(tool_name, invocation_context, model_payload)


def _early_rejection(tool_name: str) -> AgentToolResult | None:
    if is_rejected_legacy_agent_surface_name(tool_name):
        return rejected_result(tool_name, "legacy_agent_surface_rejected", "The selected name belongs to a retired Agent surface and is not callable.")
    if is_event_scoped_recovery_tool_name(tool_name):
        return rejected_result(tool_name, "event_scoped_tool_not_available", "This recovery tool is visible only through an active Kernel mirror event.")
    return None


def _rejected_payload(tool_name: str, context: Mapping[str, Any], rejected: tuple[str, ...]) -> AgentToolResult:
    invocation = AgentToolInvocation.from_values(
        tool_name=tool_name,
        invocation_context=context,
        model_payload_status="model_payload_rejected",
        client_request_id=string_or_none(context.get("client_request_id")),
        user_request_ref=string_or_none(context.get("user_request_ref")),
    )
    return rejected_result(
        tool_name,
        "model_payload_rejected",
        "The Agent-facing tool surface does not accept model-authored domain values.",
        rejected_fields=list(rejected),
        invocation=invocation.to_dict(),
    )


__all__ = [
    "AgentToolInvocationService",
    "invoke_agent_tool",
    "is_event_scoped_recovery_tool_name",
    "is_permanent_agent_tool_name",
    "is_rejected_legacy_agent_surface_name",
    "snapshot_state_files",
    "stable_json_text",
]
