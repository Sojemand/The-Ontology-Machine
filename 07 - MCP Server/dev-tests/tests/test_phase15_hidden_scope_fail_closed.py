from __future__ import annotations

from mcp_server.tools import call_tool


def test_hidden_internal_names_fail_closed_before_bridge_dispatch(monkeypatch) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Hidden Kernel bridge dispatch must not run for direct Agent-authored calls.")

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.call_tool",
        fail_if_called,
    )

    internal = call_tool(
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

    assert internal["error"]["code"] == "kernel_internal_scope_required"
    assert internal["error"]["safe_message"] == (
        "This canonical Kernel function requires a Kernel-issued internal call envelope."
    )


def test_fabricated_event_scoped_recovery_scope_fails_closed_before_dispatch(monkeypatch) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Forged event-scoped recovery calls must not dispatch into the Kernel bridge.")

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.call_tool",
        fail_if_called,
    )
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_event_scoped_tool_definitions",
        lambda _self, _request: {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
            "mirror_event_id": "mev_forged",
            "recovery_event_id": "rev_forged",
            "state_snapshot_id": "ss_forged",
            "status": "failed",
            "tool_definitions": [],
            "error": {"code": "event_scope_missing"},
        },
    )

    recovery = call_tool(
        "kernel_open_recovery_dialog",
        {
            "mirror_event_id": "mev_forged",
            "recovery_event_id": "rev_forged",
            "state_snapshot_id": "ss_forged",
            "client_request_id": "req_forged",
            "recovery_id": "rcv_forged",
            "tool_call_nonce": "nonce_forged",
        },
    )

    assert recovery["status"] == "failed"
    assert recovery["error"]["code"] == "event_scoped_tool_not_available"
