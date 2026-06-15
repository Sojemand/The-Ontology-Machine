from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.adapters.orchestrator import OrchestratorAdapter
from semantic_control_kernel.adapters.invocation import AdapterInvocation
from semantic_control_kernel.types.adapter_results import AdapterCallResult

from phase4_adapter_invocation_support import _invoke


def test_fake_owner_success_persists_full_adapter_call_contract(tmp_path: Path) -> None:
    result, call_dir, payload = _invoke(tmp_path, "success")

    assert result.status == "ok"
    for filename in (
        "request.json",
        "owner_response.raw.json",
        "response.json",
        "result.json",
        "stdout.txt",
        "stderr.txt",
        "diagnostics.json",
    ):
        assert (call_dir / filename).exists()

    request = json.loads((call_dir / "request.json").read_text(encoding="utf-8"))
    normalized_response = json.loads((call_dir / "response.json").read_text(encoding="utf-8"))
    persisted_result = json.loads((call_dir / "result.json").read_text(encoding="utf-8"))

    assert request["schema_version"] == "adapter.call_request.v1"
    assert request["request_payload"] == payload
    assert normalized_response["schema_version"] == "adapter.call_response.v1"
    assert persisted_result == result.to_dict()
    assert "fake-owner mode=success" in (call_dir / "stdout.txt").read_text(encoding="utf-8")


def test_fake_owner_error_is_converted_to_typed_result(tmp_path: Path) -> None:
    result, _call_dir, _payload = _invoke(tmp_path, "error")

    assert result.status == "owner_error"


def test_fake_owner_timeout_is_converted_to_typed_result(tmp_path: Path) -> None:
    result, _call_dir, _payload = _invoke(tmp_path, "timeout", timeout_seconds=0.2)

    assert result.status == "timeout"


def test_unbounded_owner_invocation_does_not_apply_hard_timeout(tmp_path: Path) -> None:
    result, call_dir, _payload = _invoke(
        tmp_path,
        "delayed_success",
        timeout_seconds=None,
        extra_payload={"sleep_seconds": 0.3},
    )

    request = json.loads((call_dir / "request.json").read_text(encoding="utf-8"))

    assert request["timeout_seconds"] is None
    assert result.status == "ok"


def test_orchestrator_pipeline_run_declares_unbounded_runtime(monkeypatch, tmp_path: Path) -> None:
    captured: list[AdapterInvocation] = []

    def fake_invoke(invocation: AdapterInvocation) -> AdapterCallResult:
        captured.append(invocation)
        return AdapterCallResult(
            {
                "adapter_call_id": "adc_pipeline_run",
                "adapter_name": invocation.boundary.adapter_name,
                "capability_status": invocation.boundary.capability_status,
                "diagnostics": [],
                "kernel_function": invocation.kernel_function,
                "output_refs": {},
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {
                    "artifact_root_path_hash": "sha256:artifact",
                    "database_path_hash": "sha256:database",
                },
            }
        )

    monkeypatch.setattr("semantic_control_kernel.adapters.base.invoke_owner_contract", fake_invoke)

    OrchestratorAdapter(state_root=tmp_path / "state").run_pipeline(
        {
            "workflow_run_id": "wr_unbounded",
            "target_identity": {},
        }
    )

    assert captured[0].boundary.timeout_seconds is None


def test_invalid_json_response_is_converted_to_typed_result(tmp_path: Path) -> None:
    result, _call_dir, _payload = _invoke(tmp_path, "invalid_json")

    assert result.status == "invalid_owner_response"


def test_missing_owner_response_is_converted_to_typed_result(tmp_path: Path) -> None:
    result, _call_dir, _payload = _invoke(tmp_path, "missing_response")

    assert result.status == "invalid_owner_response"
