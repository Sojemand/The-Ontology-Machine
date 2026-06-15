from __future__ import annotations

from mcp_server.semantic_control_kernel_client import SemanticControlKernelClient, SemanticControlKernelClientError
from mcp_server.tool_handlers import call_tool


def test_client_wraps_kernel_unavailable_errors_into_product_safe_failure(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise SemanticControlKernelClientError("bridge startup failed")

    monkeypatch.setattr(SemanticControlKernelClient, "_invoke_json_command", boom)

    payload = SemanticControlKernelClient().call_tool(
        tool_name="kernel_status",
        visibility="agent_visible",
        model_arguments={},
        client_context={"host_surface_identity": "mcp_server", "client_request_id": "req"},
    )

    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "semantic_control_kernel_unavailable"
    assert "traceback" not in payload["error"]["safe_message"].casefold()
    assert "inspect_workflow" not in payload["error"]["safe_message"]
    assert payload["error"]["safe_message"] == "The Semantic Control Kernel bridge is unavailable."


def test_client_masks_raw_contract_details_in_product_safe_failure(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise SemanticControlKernelClientError(
            "Traceback: token sk-phase14secret123 / inspect_workflow / C:\\\\private\\\\path"
        )

    monkeypatch.setattr(SemanticControlKernelClient, "_invoke_json_command", boom)

    payload = SemanticControlKernelClient().call_tool(
        tool_name="kernel_status",
        visibility="agent_visible",
        model_arguments={},
        client_context={"host_surface_identity": "mcp_server", "client_request_id": "req"},
    )

    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "semantic_control_kernel_unavailable"
    assert payload["error"]["safe_message"] == "The Semantic Control Kernel bridge is unavailable."
    dumped = str(payload)
    assert "sk-phase14secret" not in dumped
    assert "inspect_workflow" not in dumped
    assert "Traceback" not in dumped


def test_handler_passes_structured_failure_without_old_safe_next_actions(monkeypatch) -> None:
    def fake_call_tool(self, **kwargs):
        return {
            "schema_version": "semantic_control_kernel.mcp_response.v1",
            "status": "failed",
            "tool_name": kwargs["tool_name"],
            "effect": "none",
            "user_visible_summary": "The Kernel rejected this request.",
            "mirror_event": None,
            "error": {
                "code": "kernel_tool_rejected",
                "category": "contract_validation",
                "safe_message": "The selected tool is not available in the current Kernel state.",
            },
        }

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.call_tool",
        fake_call_tool,
    )

    response = call_tool("kernel_status", {})
    assert response["status"] == "failed"
    assert response["error"]["code"] == "kernel_tool_rejected"
    assert "inspect_workflow" not in str(response)
