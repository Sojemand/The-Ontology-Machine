from __future__ import annotations

import json

from semantic_control_kernel import mcp_contract, orchestrator_contract

from phase7_agent_invocation_support import mcp_request


def test_orchestrator_contract_honors_state_root_override_and_routes_live_workflow(tmp_path, monkeypatch) -> None:
    state_root = tmp_path / "isolated-state"
    monkeypatch.setenv("VISION_KERNEL_STATE_ROOT", str(state_root))
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(
        json.dumps({"request_id": "req-phase7", "action": "empty_database_no_semantic_release", "payload": {}}),
        encoding="utf-8",
    )

    exit_code = orchestrator_contract.main(["--request", str(request_path), "--response", str(response_path)])
    response = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert response["status"] == "ok"
    assert response["request_id"] == "req-phase7"
    assert response["result"]["status"] == "ok"
    assert "Artifact Tree" in response["result"]["user_visible_summary"]
    assert (state_root / "events" / "mirror").exists()


def test_mcp_contract_routes_representative_permanent_tools_through_current_dispatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VISION_KERNEL_STATE_ROOT", str(tmp_path / "mcp-state"))
    expected = {
        "kernel_status": None,
    }

    for tool_name, expected_code in expected.items():
        response = mcp_contract.call_mcp_tool(mcp_request(tool_name))
        if expected_code is None:
            assert response["status"] == "completed"
            assert response["error"] is None
            continue
        assert response["status"] == "blocked"
        assert response["error"]["code"] == expected_code
    manual_response = mcp_contract.call_mcp_tool(mcp_request("manual_pipeline_run"))
    assert manual_response["status"] == "accepted"
    assert manual_response["effect"] == "workflow_started"
    assert manual_response["error"] is None
    rebuild_response = mcp_contract.call_mcp_tool(mcp_request("database_rebuild_from_artifacts"))
    assert rebuild_response["status"] == "accepted"
    assert rebuild_response["effect"] == "workflow_started"
    assert rebuild_response["error"] is None
    merge_response = mcp_contract.call_mcp_tool(mcp_request("database_merge_additive_only"))
    assert merge_response["status"] == "accepted"
    assert merge_response["effect"] == "workflow_started"
    assert merge_response["error"] is None
