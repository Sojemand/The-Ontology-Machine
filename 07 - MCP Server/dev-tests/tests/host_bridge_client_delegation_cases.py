from __future__ import annotations

from mcp_server.semantic_control_kernel_client import SemanticControlKernelClientError
from mcp_server import semantic_control_kernel_client_frontend_bridge as host_bridge

from .host_bridge_support import SNAPSHOT, TARGET


def test_mcp_server_host_bridge_delegates_each_operation_to_kernel_client(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def record(method_name: str, response: dict[str, object]):
        def _method(_self, request):
            calls.append((method_name, dict(request)))
            return dict(response)

        return _method

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_client_frontend_events",
        record("list_client_frontend_events", {"schema_version": "kernel.client_frontend_event_batch.v1", "cursor": "0", "events": []}),
    )
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.submit_user_interaction_response",
        record(
            "submit_user_interaction_response",
            {
                "schema_version": "semantic_control_kernel.host_bridge_response.v1",
                "status": "accepted",
                "interaction_request_id": "ir_001",
                "user_visible_summary": "accepted",
            },
        ),
    )
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.cancel_user_interaction",
        record(
            "cancel_user_interaction",
            {
                "schema_version": "semantic_control_kernel.host_bridge_response.v1",
                "status": "cancelled",
                "interaction_request_id": "ir_001",
                "user_visible_summary": "cancelled",
            },
        ),
    )
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_event_scoped_tool_definitions",
        record(
            "list_event_scoped_tool_definitions",
            {
                "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_response.v1",
                "mirror_event_id": "mev_001",
                "recovery_event_id": "rev_001",
                "state_snapshot_id": "ss_001",
                "status": "active",
                "tool_definitions": [],
            },
        ),
    )

    events_request = {
        "schema_version": "semantic_control_kernel.client_events_request.v1",
        "cursor": "",
        "limit": 10,
        "host_surface_identity": "test_frontend",
        "client_instance_id": "client_a",
        "client_request_id": "req_events",
    }
    submit_request = {
        "schema_version": "semantic_control_kernel.interaction_response_submit.v1",
        "interaction_request_id": "ir_001",
        "response": {"schema_version": "kernel.user_interaction_response.v1"},
        "target_identity": TARGET,
        "state_snapshot_identity": SNAPSHOT,
        "host_surface_identity": "test_frontend",
        "client_request_id": "req_submit",
    }
    cancel_request = {
        "schema_version": "semantic_control_kernel.interaction_cancel_request.v1",
        "interaction_request_id": "ir_001",
        "response_status": "cancelled",
        "target_identity": TARGET,
        "state_snapshot_identity": SNAPSHOT,
        "host_surface_identity": "test_frontend",
        "client_request_id": "req_cancel",
    }
    scoped_tools_request = {
        "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
        "mirror_event_id": "mev_001",
        "recovery_event_id": "rev_001",
        "state_snapshot_id": "ss_001",
        "host_surface_identity": "test_frontend",
        "client_request_id": "req_tools",
    }

    assert host_bridge.kernel_list_client_frontend_events(events_request)["schema_version"] == "kernel.client_frontend_event_batch.v1"
    assert host_bridge.kernel_submit_user_interaction_response(submit_request)["status"] == "accepted"
    assert host_bridge.kernel_cancel_user_interaction(cancel_request)["status"] == "cancelled"
    assert host_bridge.kernel_list_event_scoped_tool_definitions(scoped_tools_request)["status"] == "active"

    assert calls == [
        ("list_client_frontend_events", events_request),
        ("submit_user_interaction_response", submit_request),
        ("cancel_user_interaction", cancel_request),
        ("list_event_scoped_tool_definitions", scoped_tools_request),
    ]


def test_mcp_server_host_bridge_fails_closed_when_kernel_client_is_unavailable(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "host_bridge.log"
    monkeypatch.setattr(host_bridge, "_bridge_log_path", lambda: log_path)

    def boom(_self, _request):
        raise SemanticControlKernelClientError("Traceback: sk-secret inspect_workflow")

    for method_name in (
        "list_client_frontend_events",
        "submit_user_interaction_response",
        "cancel_user_interaction",
        "list_event_scoped_tool_definitions",
    ):
        monkeypatch.setattr(f"mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.{method_name}", boom)

    events = host_bridge.kernel_list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "",
            "limit": 10,
            "host_surface_identity": "test_frontend",
            "client_instance_id": "client_a",
            "client_request_id": "req_events",
        }
    )
    submit = host_bridge.kernel_submit_user_interaction_response(
        {
            "schema_version": "semantic_control_kernel.interaction_response_submit.v1",
            "interaction_request_id": "ir_001",
            "response": {"schema_version": "kernel.user_interaction_response.v1"},
            "target_identity": TARGET,
            "state_snapshot_identity": SNAPSHOT,
            "host_surface_identity": "test_frontend",
            "client_request_id": "req_submit",
        }
    )
    cancel = host_bridge.kernel_cancel_user_interaction(
        {
            "schema_version": "semantic_control_kernel.interaction_cancel_request.v1",
            "interaction_request_id": "ir_001",
            "response_status": "cancelled",
            "target_identity": TARGET,
            "state_snapshot_identity": SNAPSHOT,
            "host_surface_identity": "test_frontend",
            "client_request_id": "req_cancel",
        }
    )
    scoped = host_bridge.kernel_list_event_scoped_tool_definitions(
        {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
            "mirror_event_id": "mev_001",
            "recovery_event_id": "rev_001",
            "state_snapshot_id": "ss_001",
            "host_surface_identity": "test_frontend",
            "client_request_id": "req_tools",
        }
    )

    assert events == {"schema_version": "kernel.client_frontend_event_batch.v1", "cursor": "0", "events": []}
    assert submit["status"] == "failed"
    assert cancel["status"] == "failed"
    assert scoped["status"] == "failed"
    assert scoped["tool_definitions"] == []
    assert "[redacted-secret]" in submit["error"]["detail"]
    assert "[redacted-tool]" in submit["error"]["detail"]
    assert "sk-secret" not in str((events, submit, cancel, scoped))
    assert "inspect_workflow" not in str((events, submit, cancel, scoped))
    log_text = log_path.read_text(encoding="utf-8")
    assert "[redacted-secret]" in log_text
    assert "[redacted-tool]" in log_text
    assert "sk-secret" not in log_text
    assert "inspect_workflow" not in log_text


def test_mcp_server_host_bridge_rotates_exception_log(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "host_bridge.log"
    backup_path = tmp_path / "host_bridge.log.1"
    log_path.write_text("x" * 120, encoding="utf-8")
    backup_path.write_text("older", encoding="utf-8")
    monkeypatch.setattr(host_bridge, "_BRIDGE_LOG_MAX_BYTES", 125)
    monkeypatch.setattr(host_bridge, "_BRIDGE_LOG_BACKUP_COUNT", 2)

    host_bridge._append_bridge_log(log_path, "fresh\n")

    assert log_path.read_text(encoding="utf-8") == "fresh\n"
    assert (tmp_path / "host_bridge.log.1").read_text(encoding="utf-8") == "x" * 120
    assert (tmp_path / "host_bridge.log.2").read_text(encoding="utf-8") == "older"
