from __future__ import annotations

import json
import sys
from pathlib import Path

from semantic_control_kernel.adapters.base import BasePipelineAdapter
from semantic_control_kernel.debug.adapter_diagnostics import AdapterDiagnosticRecorder
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.repository.trace_store import TraceLinkStore


MODULE_ROOT = Path(__file__).resolve().parents[2]
FAKE_OWNER_ROOT = MODULE_ROOT / "dev-tests" / "fixtures" / "adapters"


def test_adapter_diagnostics_cover_success_blocker_timeout_missing_and_uncertain(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    recorder = AdapterDiagnosticRecorder(paths)
    run = WorkflowRunStore(paths).create_run(
        "pipeline_run",
        {"target_hash": "adapter_target"},
        "phase18_adapter_test",
    )

    recorder.record_result(
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        adapter_name="WorkspaceAdapter",
        owner_module="00 - Orchestrator",
        owner_action="run",
        adapter_call_id="adc_success",
        status="ok",
        started_at="2026-05-06T09:00:00Z",
        request_ref="adapter_calls/adc_success/request.json",
        response_ref="adapter_calls/adc_success/owner_response.raw.json",
    )
    recorder.record_result(
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        adapter_name="WorkspaceAdapter",
        owner_module="00 - Orchestrator",
        owner_action="run",
        adapter_call_id="adc_blocked",
        status="blocked_by_kernel_precondition",
        started_at="2026-05-06T09:00:00Z",
        request_ref="adapter_calls/adc_blocked/request.json",
        response_ref="adapter_calls/adc_blocked/owner_response.raw.json",
    )
    recorder.record_result(
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        adapter_name="WorkspaceAdapter",
        owner_module="00 - Orchestrator",
        owner_action="run",
        adapter_call_id="adc_missing",
        status="missing_capability",
        started_at="2026-05-06T09:00:00Z",
        request_ref="adapter_calls/adc_missing/request.json",
        response_ref="adapter_calls/adc_missing/owner_response.raw.json",
    )
    recorder.record_result(
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        adapter_name="WorkspaceAdapter",
        owner_module="00 - Orchestrator",
        owner_action="run",
        adapter_call_id="adc_timeout",
        status="timeout",
        started_at="2026-05-06T09:00:00Z",
        request_ref="adapter_calls/adc_timeout/request.json",
        response_ref="adapter_calls/adc_timeout/owner_response.raw.json",
    )
    recorder.record_result(
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        adapter_name="WorkspaceAdapter",
        owner_module="00 - Orchestrator",
        owner_action="run",
        adapter_call_id="adc_failed",
        status="owner_error",
        started_at="2026-05-06T09:00:00Z",
        request_ref="adapter_calls/adc_failed/request.json",
        response_ref="adapter_calls/adc_failed/owner_response.raw.json",
    )
    recorder.record_result(
        workflow_run_id=run.workflow_run_id,
        workflow_tool=run.workflow_tool,
        adapter_name="WorkspaceAdapter",
        owner_module="00 - Orchestrator",
        owner_action="run",
        adapter_call_id="adc_uncertain",
        status="owner_error",
        started_at="2026-05-06T09:00:00Z",
        request_ref="adapter_calls/adc_uncertain/request.json",
        response_ref="adapter_calls/adc_uncertain/owner_response.raw.json",
        mutating=True,
    )

    records = []
    for path in sorted((paths.state_root / "debug" / "adapter_calls" / run.workflow_run_id).glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))

    statuses = {item["status"] for item in records}
    assert statuses == {
        "succeeded",
        "blocked",
        "missing_capability",
        "timed_out",
        "failed",
        "uncertain_partial_mutation",
    }
    assert all(item["request_ref"].startswith("adapter_calls/") for item in records)
    assert all(item["response_ref"].startswith("adapter_calls/") for item in records)
    assert all(item["redaction_profile"]["profile_id"] == "support_safe_v1" for item in records)
    assert len([link for link in TraceLinkStore(paths).list_links_for_workflow(run.workflow_run_id) if link["object_kind"] == "adapter_call_diagnostic"]) == 6


def test_base_adapter_invoke_emits_adapter_diagnostic_at_runtime_boundary(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run(
        "create_empty_database",
        {"database_path_hash": "database_hash_123"},
        "phase18_adapter_boundary",
    )
    adapter = BasePipelineAdapter(
        state_root=paths.state_root,
        owner_roots={"fake_corpus_builder": FAKE_OWNER_ROOT},
        python_executable=Path(sys.executable),
    )

    result = adapter.invoke(
        kernel_function="create_empty_database",
        owner_module="fake_corpus_builder",
        owner_contract_module="fakes.fake_owner",
        owner_action="create_empty_corpus_db",
        request_payload={"mode": "success", "target_identity_proof": {"database_path_hash": "database_hash_123"}},
        capability_status="implemented_in_pipeline",
        timeout_seconds=5,
        mutating=True,
        required_target_proof_fields=("database_path|database_path_hash",),
        target_identity={"database_path_hash": "database_hash_123"},
        workflow_run_id=run.workflow_run_id,
    )

    records = list((paths.state_root / "debug" / "adapter_calls" / run.workflow_run_id).glob("*.json"))
    assert result.status == "ok"
    assert len(records) == 1
    diagnostic = json.loads(records[0].read_text(encoding="utf-8"))
    assert diagnostic["status"] == "succeeded"
    assert diagnostic["adapter_call_id"] == result.adapter_call_id
    assert diagnostic["request_ref"] == f"adapter_calls/{result.adapter_call_id}/request.json"
    assert any(
        link["object_kind"] == "adapter_call_diagnostic" and link["object_id"] == result.adapter_call_id
        for link in TraceLinkStore(paths).list_links_for_workflow(run.workflow_run_id)
    )
