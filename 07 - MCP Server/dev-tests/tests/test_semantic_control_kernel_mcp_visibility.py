from __future__ import annotations

from mcp_server.semantic_control_kernel_visibility import authorize_tool_call, tool_visibility


def test_visibility_classifies_permanent_event_scoped_internal_continuation_host_only_legacy_and_unknown_names() -> None:
    assert tool_visibility("kernel_status") == "agent_visible"
    assert tool_visibility("kernel_open_recovery_dialog") == "event_scoped"
    assert tool_visibility("create_empty_database") == "kernel_internal"
    assert tool_visibility("reingest_pipeline_batch") == "unknown"
    assert tool_visibility("kernel_list_client_frontend_events") == "host_only_client_bridge"
    assert tool_visibility("open_workflow") == "legacy_hidden"
    assert tool_visibility("not_a_real_tool") == "unknown"


def test_direct_legacy_internal_and_continuation_calls_fail_closed() -> None:
    legacy = authorize_tool_call("open_workflow", {})
    internal = authorize_tool_call("create_empty_database", {})
    event_scoped = authorize_tool_call(
        "kernel_open_recovery_dialog",
        {
            "mirror_event_id": "mev_001",
            "recovery_event_id": "rev_001",
            "state_snapshot_id": "ss_001",
            "client_request_id": "req_001",
        },
    )

    assert legacy["response"]["error"]["code"] == "legacy_kernel_surface_retired"
    assert internal["response"]["error"]["code"] == "kernel_internal_scope_required"
    assert authorize_tool_call("reingest_pipeline_batch", {})["enforce_permissions"] is True
    assert event_scoped["response"]["error"]["code"] == "event_scoped_tool_not_available"
