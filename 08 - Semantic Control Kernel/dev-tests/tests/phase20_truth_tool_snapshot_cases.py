from __future__ import annotations

from pathlib import Path

from phase20_go_live_support import load_json
from phase20_truth_support import module


def test_tool_snapshots_follow_live_surface_contracts(monkeypatch, tmp_path: Path) -> None:
    empty_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    fake_contracts = {
        "public_tool_definitions": [
            {"name": "tool_from_mcp_a", "description": "A", "inputSchema": empty_schema},
            {"name": "tool_from_mcp_b", "description": "B", "inputSchema": empty_schema},
        ],
        "public_tool_names": ["tool_from_mcp_a", "tool_from_mcp_b"],
        "mcp_permanent_tool_names": ["tool_from_mcp_a", "tool_from_mcp_b"],
        "mcp_event_scoped_tool_names": ["recovery_from_mcp"],
        "mcp_kernel_internal_tool_names": ["internal_from_mcp"],
        "mcp_continuation_tool_names": ["continuation_from_mcp"],
        "mcp_host_only_client_bridge_names": ["host_bridge_from_mcp"],
        "mcp_legacy_retired_tool_names": ["retired_from_mcp"],
        "mcp_kernel_internal_scope_fields": ["internal_scope_a"],
        "mcp_continuation_scope_fields": ["continuation_scope_a", "continuation_scope_b"],
        "mcp_event_scoped_scope_fields": {"recovery_from_mcp": ["scope_a", "scope_b"]},
        "frontend_permanent_tool_names": ["tool_from_mcp_a", "tool_from_mcp_b"],
        "frontend_event_scoped_tool_names": ["recovery_from_mcp"],
        "kernel_permanent_tool_names": ["tool_from_mcp_a", "tool_from_mcp_b"],
        "kernel_event_scoped_tool_names": ["recovery_from_mcp"],
        "parity": {
            "public_matches_mcp_visibility": True,
            "mcp_matches_frontend_permanent_surface": True,
            "mcp_matches_kernel_permanent_surface": True,
            "mcp_matches_frontend_recovery_surface": True,
            "mcp_matches_kernel_recovery_surface": True,
        },
    }
    monkeypatch.setattr(module, "_live_tool_surface_contracts", lambda: fake_contracts)

    module._write_tool_snapshots(tmp_path, "glv_unit")

    public = load_json(tmp_path / "mcp_public_agent_snapshot.json")
    internal = load_json(tmp_path / "mcp_kernel_internal_contract_snapshot.json")
    continuation = load_json(tmp_path / "mcp_continuation_scope_snapshot.json")

    assert [tool["name"] for tool in public["tool_definitions"]] == ["tool_from_mcp_a", "tool_from_mcp_b"]
    assert internal["kernel_internal_tools"] == ["internal_from_mcp"]
    assert internal["event_scoped_scope_fields"] == {"recovery_from_mcp": ["scope_a", "scope_b"]}
    assert continuation["required_hidden_fields"] == ["continuation_scope_a", "continuation_scope_b"]


def test_phase19_evidence_does_not_claim_happy_path_success_before_live_matrix_passes(tmp_path: Path) -> None:
    path = module._write_phase19_evidence(tmp_path, "glv_unit", [])
    payload = load_json(path)

    assert payload["evidence_status"] == "owner_tested_live_command_execution_pending"
    for capability in payload["capabilities"]:
        assert capability["missing_capability_happy_path_result"] == "verification_pending"
        assert capability["live_verification_status"] == "pending_or_failed_live_matrix"
        receipt = load_json(tmp_path / capability["capability_receipt_sample_refs"][0])
        assert receipt["result_status"] == "unverified"
        assert receipt["diagnostics"][0]["code"] == "live_command_execution_pending"


def test_phase20_truth_hash_tracks_runtime_event_and_support_sources() -> None:
    truth_inputs = {path.relative_to(module.PIPELINE_ROOT).as_posix() for path in module.PHASE20_TRUTH_INPUTS}

    assert "08 - Semantic Control Kernel/semantic_control_kernel/surface/client_frontend_bridge.py" in truth_inputs
    assert "08 - Semantic Control Kernel/semantic_control_kernel/repository/support_bundles.py" in truth_inputs
