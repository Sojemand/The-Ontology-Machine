from __future__ import annotations

from phase14_mcp_contract_support import mcp_request
from semantic_control_kernel import mcp_contract


def test_mcp_contract_preserves_support_state_fields_from_agent_tool_results(monkeypatch) -> None:
    class _FakeResult:
        def to_dict(self) -> dict[str, object]:
            return {
                "schema_version": "agent_tool_result.v1",
                "tool_name": "kernel_status",
                "status": "ok",
                "effect": "read",
                "user_visible_summary": "Kernel status was read without changing workflow state.",
                "active_state": {"support_status": "read_only", "active_workflow_run_count": 0},
                "resume_state": {"resumable_count": 1},
                "diagnostic_ref": "diag_phase14",
                "error": None,
            }

    monkeypatch.setattr("semantic_control_kernel.mcp_contract.invoke_agent_tool", lambda *_args, **_kwargs: _FakeResult())

    response = mcp_contract.call_mcp_tool(
        mcp_request(
            "kernel_status",
            visibility="agent_visible",
            event_scope=None,
        )
    )

    assert response["status"] == "completed"
    assert response["active_state"]["support_status"] == "read_only"
    assert response["resume_state"]["resumable_count"] == 1
    assert response["diagnostic_ref"] == "diag_phase14"
