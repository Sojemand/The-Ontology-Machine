from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.partial_pipeline_run import PartialPipelineRunReconciler
from semantic_control_kernel.domain.recovery.staged_work_archive import StagedWorkArchiveService
from semantic_control_kernel.domain.recovery.stale_lock import StaleLockRecoveryService
from semantic_control_kernel.domain.recovery.tool_authorization import RecoveryToolAuthorization
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.lock_store import LockStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.surface.agent_invocation import default_state_paths, invoke_agent_tool
from semantic_control_kernel.surface.client_frontend_bridge import (
    cancel_user_interaction as bridge_cancel_user_interaction,
    list_client_frontend_events as bridge_list_client_frontend_events,
    list_event_scoped_tool_definitions as bridge_list_event_scoped_tool_definitions,
    submit_user_interaction_response as bridge_submit_user_interaction_response,
)
from semantic_control_kernel.surface.mcp_tools import list_mcp_tool_definitions as surface_list_mcp_tool_definitions
from semantic_control_kernel.surface.recovery_tools import RecoveryToolSurface
from semantic_control_kernel.surface.mcp_tool_schemas import (
    KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES,
)
from semantic_control_kernel.surface.mcp_visibility import is_event_scoped_tool, is_legacy_retired_name, is_permanent_agent_tool
from semantic_control_kernel.types.mcp import MCP_SCOPE_ALL, MCP_SCOPE_EVENT_SCOPED_RECOVERY, MCP_SCOPE_KERNEL_INTERNAL, MCP_SCOPE_PERMANENT_AGENT
from semantic_control_kernel.mcp_event_scope import (
    check_event_scoped_tool as _check_event_scoped_tool,
    event_scoped_tool_payload as _event_scoped_tool_payload,
)
from semantic_control_kernel.mcp_responses import (
    accepted_response as _accepted_response,
    agent_result_response as _agent_result_response_impl,
    failure_response as _failure_response,
    legacy_retired_response as _legacy_retired_response,
    recovery_output_response as _recovery_output_response,
)
from semantic_control_kernel.validation.mcp_validation import (
    MCPContractError,
    require_hidden_scope,
    validate_mcp_request_envelope,
    validate_tool_definition_list,
)


def list_mcp_tool_definitions(scope: str) -> dict[str, Any]:
    payload = surface_list_mcp_tool_definitions(scope, state_paths=_state_paths())
    validate_tool_definition_list(payload)
    return payload


def call_mcp_tool(envelope: Mapping[str, Any]) -> dict[str, Any]:
    validate_mcp_request_envelope(envelope)
    tool_name = str(envelope["tool_name"])
    if is_legacy_retired_name(tool_name):
        return _legacy_retired_response(tool_name)
    if is_permanent_agent_tool(tool_name):
        return _call_permanent_tool(tool_name, envelope)
    if is_event_scoped_tool(tool_name):
        return _call_event_scoped_tool(tool_name, envelope)
    if tool_name in KERNEL_INTERNAL_TOOL_NAMES:
        scope = require_hidden_scope(
            envelope.get("event_scope"),
            "kernel_internal_call_id",
            "workflow_run_id",
            "state_snapshot_id",
            "tool_name",
            "arguments",
        )
        return _accepted_response(
            tool_name,
            effect="kernel_internal_scope_validated",
            summary="The Kernel accepted the internal canonical function envelope.",
            workflow_run_id=scope["workflow_run_id"],
        )
    if tool_name in KERNEL_CONTINUATION_TOOL_NAMES:
        scope = require_hidden_scope(
            envelope.get("event_scope"),
            "kernel_continuation_id",
            "workflow_run_id",
            "state_snapshot_id",
            "resume_state_id",
            "operation_name",
            "arguments",
            "source_manifest_ref",
            "input_refs",
        )
        return _accepted_response(
            tool_name,
            effect="kernel_continuation_scope_validated",
            summary="The Kernel accepted the continuation-scoped operation envelope.",
            workflow_run_id=scope["workflow_run_id"],
        )
    return _failure_response(
        tool_name,
        code="kernel_tool_rejected",
        category="contract_validation",
        safe_message="The selected tool is not available in the current Kernel state.",
    )


def check_event_scoped_tool(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return _check_event_scoped_tool(envelope, state_paths=_state_paths())


def kernel_healthcheck() -> dict[str, Any]:
    module_root = _module_root()
    paths = _state_paths(create_layout=False)
    return {
        "status": "ok",
        "available": True,
        "module_root": str(module_root),
        "state_root": str(paths.state_root),
        "scopes": [
            MCP_SCOPE_PERMANENT_AGENT,
            MCP_SCOPE_EVENT_SCOPED_RECOVERY,
            MCP_SCOPE_KERNEL_INTERNAL,
            MCP_SCOPE_ALL,
        ],
    }


def list_client_frontend_events(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return bridge_list_client_frontend_events(envelope, state_paths=_state_paths(create_layout=False))


def submit_user_interaction_response(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return bridge_submit_user_interaction_response(envelope, state_paths=_state_paths(), continue_inline=None)


def cancel_user_interaction(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return bridge_cancel_user_interaction(envelope, state_paths=_state_paths())


def list_event_scoped_tool_definitions(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return bridge_list_event_scoped_tool_definitions(envelope, state_paths=_state_paths(create_layout=False))


def _call_event_scoped_tool(tool_name: str, envelope: Mapping[str, Any]) -> dict[str, Any]:
    paths = _state_paths()
    check = _check_event_scoped_tool(envelope, state_paths=paths)
    if not check["allowed"]:
        return _failure_response(
            tool_name,
            code="event_scoped_tool_not_available",
            category="contract_validation",
            safe_message="The selected recovery tool is not available in the current Kernel state.",
        )
    try:
        payload = _event_scoped_tool_payload(tool_name, envelope.get("event_scope"))
    except MCPContractError:
        return _failure_response(
            tool_name,
            code="event_scoped_tool_not_available",
            category="contract_validation",
            safe_message="The selected recovery tool is not available in the current Kernel state.",
        )
    recovery_store = RecoveryEventStore(paths)
    output = RecoveryToolSurface(
        authorization=RecoveryToolAuthorization(recovery_store, MirrorEventStore(paths)),
        partial_run_reconciler=PartialPipelineRunReconciler(paths, recovery_store),
        recovery_store=recovery_store,
        staged_work_service=StagedWorkArchiveService(paths, recovery_store),
        stale_lock_service=StaleLockRecoveryService(LockStore(paths), recovery_store),
    ).call(tool_name, payload)
    return _recovery_output_response(
        tool_name,
        output,
        workflow_run_id=_string_or_none(check.get("workflow_run_id")),
        mirror_event=check.get("mirror_event"),
    )


def _call_permanent_tool(tool_name: str, envelope: Mapping[str, Any]) -> dict[str, Any]:
    result = invoke_agent_tool(
        tool_name,
        invocation_context=dict(envelope.get("client_context") or {}),
        model_payload=dict(envelope.get("model_arguments") or {}),
    ).to_dict()
    return _agent_result_response(tool_name, result)


def _agent_result_response(tool_name: str, result: Mapping[str, Any]) -> dict[str, Any]:
    return _agent_result_response_impl(tool_name, result)


def _module_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _state_paths(*, create_layout: bool = True) -> StatePaths:
    return default_state_paths(create_layout=create_layout)


def _string_or_none(value: object) -> str | None:
    return str(value) if value not in (None, "") else None
