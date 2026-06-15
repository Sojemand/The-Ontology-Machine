from __future__ import annotations

import pytest

from mcp_server.tool_handlers import call_tool
from mcp_server.tool_handler_types import ToolFailure


def test_handlers_forward_canonical_tools_with_expected_visibility_and_empty_model_arguments(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_call_tool(self, **kwargs):
        calls.append(dict(kwargs))
        return {
            "schema_version": "semantic_control_kernel.mcp_response.v1",
            "status": "accepted",
            "tool_name": kwargs["tool_name"],
            "effect": "workflow_started",
            "user_visible_summary": "ok",
            "mirror_event": None,
            "error": None,
        }

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.call_tool",
        fake_call_tool,
    )

    result_creation = call_tool("empty_database_default_taxonomy_default_projections", {})
    result_creation_projectionless = call_tool("empty_database_default_taxonomy_no_projections", {})
    result_custom_taxonomy = call_tool("create_custom_taxonomy_path", {})
    result_rebuild = call_tool("database_rebuild_from_artifacts", {})
    result_support = call_tool("kernel_status", {})
    result_resume_continue = call_tool("kernel_continue_resumable_workflow", {"resume_option_ref": "opaque:resume_001"})
    with pytest.raises(ToolFailure):
        call_tool("reingest_pipeline_batch", {})
    internal_scoped = call_tool(
        "create_empty_database",
        {
            "kernel_internal_call_id": "kic_001",
            "workflow_run_id": "wr_001",
            "state_snapshot_id": "ss_001",
            "tool_name": "create_empty_database",
            "arguments": {},
            "client_request_id": "req_001",
        },
    )

    assert result_creation["tool_name"] == "empty_database_default_taxonomy_default_projections"
    assert result_creation_projectionless["tool_name"] == "empty_database_default_taxonomy_no_projections"
    assert result_custom_taxonomy["tool_name"] == "create_custom_taxonomy_path"
    assert result_rebuild["tool_name"] == "database_rebuild_from_artifacts"
    assert result_support["tool_name"] == "kernel_status"
    assert result_resume_continue["tool_name"] == "kernel_continue_resumable_workflow"
    assert internal_scoped["error"]["code"] == "kernel_internal_scope_required"

    assert [call["tool_name"] for call in calls] == [
        "empty_database_default_taxonomy_default_projections",
        "empty_database_default_taxonomy_no_projections",
        "create_custom_taxonomy_path",
        "database_rebuild_from_artifacts",
        "kernel_status",
        "kernel_continue_resumable_workflow",
    ]
    assert all(call["model_arguments"] == {} for call in calls[:6])
    assert calls[-1]["client_context"]["resume_option_ref"] == "opaque:resume_001"
    assert all(call["visibility"] == "agent_visible" for call in calls[:6])
    assert all(call["visibility"] == "agent_visible" for call in calls)


def test_event_scoped_handlers_forward_full_hidden_scope_without_model_payload(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_list_event_scoped_tools(self, request):
        return {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
            "mirror_event_id": request["mirror_event_id"],
            "recovery_event_id": request["recovery_event_id"],
            "state_snapshot_id": request["state_snapshot_id"],
            "status": "active",
            "tool_definitions": [
                {
                    "name": "kernel_open_recovery_dialog",
                    "description": "Open the active Kernel recovery dialog.",
                    "inputSchema": {"type": "object", "properties": {}, "required": []},
                }
            ],
        }

    def fake_call_tool(self, **kwargs):
        calls.append(dict(kwargs))
        return {
            "schema_version": "semantic_control_kernel.mcp_response.v1",
            "status": "completed",
            "tool_name": kwargs["tool_name"],
            "effect": "recovery_action_applied",
            "user_visible_summary": "ok",
            "mirror_event": {"mirror_event_id": "mev_001"},
            "error": None,
            "recovery_receipt_id": "rcr_001",
            "dialog_request_ref": "dlg_001",
        }

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_event_scoped_tool_definitions",
        fake_list_event_scoped_tools,
    )
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.call_tool",
        fake_call_tool,
    )

    result = call_tool(
        "kernel_open_recovery_dialog",
        {
            "mirror_event_id": "mev_001",
            "recovery_event_id": "rev_001",
            "state_snapshot_id": "ss_001",
            "client_request_id": "req_001",
            "recovery_id": "rcv_001",
            "tool_call_nonce": "nonce_001",
            "conversation_ref": "conv_001",
            "turn_ref": "turn_001",
        },
    )

    assert result["status"] == "completed"
    assert result["recovery_receipt_id"] == "rcr_001"
    assert result["dialog_request_ref"] == "dlg_001"
    assert len(calls) == 1
    assert calls[0]["tool_name"] == "kernel_open_recovery_dialog"
    assert calls[0]["visibility"] == "event_scoped"
    assert calls[0]["model_arguments"] == {}
    assert calls[0]["client_context"]["conversation_ref"] == "conv_001"
    assert calls[0]["client_context"]["turn_ref"] == "turn_001"
    assert calls[0]["event_scope"]["mirror_event_id"] == "mev_001"
    assert calls[0]["event_scope"]["recovery_event_id"] == "rev_001"
    assert calls[0]["event_scope"]["state_snapshot_id"] == "ss_001"
    assert calls[0]["event_scope"]["client_request_id"] == "req_001"
    assert calls[0]["event_scope"]["recovery_id"] == "rcv_001"
    assert calls[0]["event_scope"]["tool_call_nonce"] == "nonce_001"
