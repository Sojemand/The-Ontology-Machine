from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_tool_invocation_service import AgentToolInvocationService
from semantic_control_kernel.types.agent_tools import AgentToolResult

STATE_ROOT_OVERRIDE_ENV = "VISION_KERNEL_STATE_ROOT"


def default_state_paths(*, create_layout: bool = True) -> StatePaths:
    module_root = Path(__file__).resolve().parents[2]
    override = os.environ.get(STATE_ROOT_OVERRIDE_ENV)
    if override:
        paths = StatePaths(module_root=module_root, state_root=Path(override).resolve(strict=False))
    else:
        paths = StatePaths.from_module_root(module_root)
    if create_layout:
        paths.ensure_layout()
    return paths


def invoke_agent_tool(
    tool_name: str,
    invocation_context: Mapping[str, Any] | None = None,
    model_payload: Mapping[str, Any] | None = None,
    *,
    service: AgentToolInvocationService | None = None,
) -> AgentToolResult:
    invocation_service = service or AgentToolInvocationService(state_paths=default_state_paths())
    return invocation_service.invoke(
        tool_name,
        invocation_context=invocation_context,
        model_payload=model_payload,
    )
