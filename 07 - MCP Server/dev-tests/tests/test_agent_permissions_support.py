from __future__ import annotations

from pathlib import Path

from tests.agent_permissions_contract_support import copy_module, invoke_contract


def test_mcp_server_edit_contract_runs_support_monitor_actions(tmp_path: Path) -> None:
    module_root = copy_module(tmp_path)
    recorded = invoke_contract(
        module_root,
        {
            "action": "assess_support_incident",
            "classification": "unexpected_exception",
            "confidence": "high",
            "module_key": "normalizer",
            "tool_action": "compile_release_package",
            "severity": "error",
            "status": "exception",
            "message": "compile failed with token sk-editcontractsecret123456",
        },
    )
    assessment_id = recorded["assessment"]["assessment_id"]
    incident_id = recorded["assessment"]["incident_id"]

    listed = invoke_contract(module_root, {"action": "list_support_incidents"})
    preview = invoke_contract(module_root, {"action": "preview_support_bug_report", "assessment_id": assessment_id})
    built = invoke_contract(module_root, {"action": "build_support_bug_report", "assessment_id": assessment_id})
    submitted = invoke_contract(
        module_root,
        {
            "action": "queue_support_bug_report",
            "assessment_id": assessment_id,
            "report_path": built["report_path"],
            "user_confirmed": True,
        },
    )
    dismissed = invoke_contract(
        module_root,
        {"action": "dismiss_support_incident", "incident_id": incident_id, "reason": "test"},
    )

    assert listed["incident_count"] == 1
    assert preview["report"]["incident"]["incident_id"] == incident_id
    assert Path(built["report_path"]).exists()
    assert Path(submitted["queued_path"]).exists()
    assert dismissed["dismissed"] is True
