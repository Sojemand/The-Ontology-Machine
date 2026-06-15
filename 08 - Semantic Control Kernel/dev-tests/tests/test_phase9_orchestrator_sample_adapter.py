from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.adapters.invocation import AdapterInvocation
from semantic_control_kernel.adapters.orchestrator import OrchestratorAdapter
from semantic_control_kernel.types.adapter_results import AdapterCallResult


def test_inspect_source_sample_declares_owner_action(monkeypatch, tmp_path: Path) -> None:
    captured: list[AdapterInvocation] = []

    def fake_invoke(invocation: AdapterInvocation) -> AdapterCallResult:
        captured.append(invocation)
        return AdapterCallResult(
            {
                "adapter_call_id": "adc_sample_action",
                "adapter_name": invocation.boundary.adapter_name,
                "capability_status": invocation.boundary.capability_status,
                "diagnostics": [],
                "kernel_function": invocation.kernel_function,
                "output_refs": {"raw_extract_paths": []},
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {},
            }
        )

    monkeypatch.setattr("semantic_control_kernel.adapters.base.invoke_owner_contract", fake_invoke)

    OrchestratorAdapter(state_root=tmp_path / "state", pipeline_root=tmp_path).inspect_source_sample(
        {
            "source_document_path": str(tmp_path / "sample.pdf"),
            "workflow_run_id": "wr_sample_action",
        }
    )

    assert captured[0].boundary.owner_action == "inspect_source_document_sample"
    assert captured[0].request_payload["action"] == "inspect_source_document_sample"
    assert captured[0].workflow_run_id == "wr_sample_action"
    assert "workflow_run_id" not in captured[0].request_payload
