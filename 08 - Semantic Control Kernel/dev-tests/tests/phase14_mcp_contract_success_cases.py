from __future__ import annotations

from pathlib import Path

from phase14_mcp_contract_support import active_event, mcp_request
from semantic_control_kernel import mcp_contract


def test_event_scoped_mcp_call_executes_recovery_surface_and_preserves_output(tmp_path: Path, monkeypatch) -> None:
    paths, mirror_event_id, options = active_event(tmp_path)
    option = options[0].payload
    calls: list[dict[str, object]] = []

    def fake_call(self, tool_name, payload, *, service_evidence=None):  # noqa: ANN001
        calls.append({"tool_name": tool_name, "payload": dict(payload)})
        return {
            "schema_version": "kernel.kernel_open_recovery_dialog.output.v1",
            "result_status": "applied",
            "recovery_receipt_id": "rcr_phase14",
            "dialog_request_ref": "dlg_phase14",
            "kernel_dialog_state": {"dialog": "reopened"},
        }

    monkeypatch.setenv("VISION_KERNEL_STATE_ROOT", str(paths.state_root))
    monkeypatch.setattr("semantic_control_kernel.mcp_contract.RecoveryToolSurface.call", fake_call)

    response = mcp_contract.call_mcp_tool(
        mcp_request(
            "kernel_open_recovery_dialog",
            visibility="event_scoped",
            event_scope={
                "mirror_event_id": mirror_event_id,
                "recovery_event_id": "rev_phase14_contract",
                "state_snapshot_id": "ss_phase14_contract",
                "client_request_id": "req_phase14_contract",
                "recovery_id": option["recovery_id"],
                "tool_call_nonce": "nonce_phase14",
            },
        )
    )

    assert response["status"] == "completed"
    assert response["effect"] == "recovery_action_applied"
    assert response["recovery_receipt_id"] == "rcr_phase14"
    assert response["dialog_request_ref"] == "dlg_phase14"
    assert response["kernel_dialog_state"] == {"dialog": "reopened"}
    assert len(calls) == 1
    assert calls[0]["tool_name"] == "kernel_open_recovery_dialog"
    assert calls[0]["payload"]["recovery_id"] == option["recovery_id"]
    assert calls[0]["payload"]["tool_call_nonce"] == "nonce_phase14"
