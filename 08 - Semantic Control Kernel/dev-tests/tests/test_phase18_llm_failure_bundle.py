from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.adapters.llm_adapter import LLMFunctionAdapter
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.types.llm_calls import LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner


MODULE_ROOT = Path(__file__).resolve().parents[2]
VALID_LLM_FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


class AlwaysInvalidProvider(LLMFunctionAdapter):
    def generate(self, request, cancellation=None):
        return LLMProviderResponse(
            provider="fake",
            model=request.model,
            response_id=f"response_{request.attempt_index}",
            status="complete",
            output_text="not valid json with secret sk-test-123456789",
            raw_provider_response_ref={"response_id": f"response_{request.attempt_index}"},
            usage={},
            finish_reason="stop",
        )


class SequenceProvider(LLMFunctionAdapter):
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.requests = []

    def generate(self, request, cancellation=None):
        self.requests.append(request)
        return LLMProviderResponse(
            provider="fake",
            model=request.model,
            response_id=f"response_{len(self.requests)}",
            status="complete",
            output_text=self.outputs[len(self.requests) - 1],
            raw_provider_response_ref={},
            usage={},
            finish_reason="stop",
        )


def test_final_llm_validation_bundle_links_failed_attempts_and_keeps_raw_payloads_out_of_bundle(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run(
        "analyze_samples",
        {"target_hash": "phase18_llm"},
        "phase18_llm_test",
    )
    runner = LLMCallRunner(
        AlwaysInvalidProvider(),
        artifact_root=tmp_path / "artifacts",
        state_root=tmp_path / "state",
    )
    result = runner.run(
        "analyze_samples",
        workflow_run_id=run.workflow_run_id,
        analysis_run_id="ana_llm_phase18",
        input_payload=[{"sample_id": "sample-1", "text": "example"}],
        runtime_settings={
            "semantic_control_kernel_llm": {
                "model": "gpt-test",
                "max_output_tokens": 256,
                "provider_family": "fake",
            }
        },
        preserved_state_summary={"safe_to_retry": True, "resumable_state": True, "cancellable": True},
    )

    assert result.status == "failed_final_validation"
    support_ref = result.final_error.support_bundle_ref
    manifest_path = tmp_path / "state" / support_ref["support_bundle_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle_dir = manifest_path.parent

    assert manifest["support_bundle_id"] == support_ref["support_bundle_id"]
    assert len(manifest["llm_attempt_diagnostic_refs"]) == 3
    assert len(manifest["failed_attempt_artifact_refs"]) == 3
    assert manifest["redaction_report_ref"] == f"debug/redaction_reports/{support_ref['support_bundle_id']}.json"
    assert set(result.mirror_event["allowed_agent_tools"]) == {
        "kernel_retry_recoverable_workflow",
        "kernel_cancel_active_run",
        "kernel_resume_state",
        "kernel_open_support_bundle",
    }

    bundle_text = "\n".join(
        (bundle_dir / name).read_text(encoding="utf-8")
        for name in ("support_bundle_manifest.json", "safe_summary.md", "included_refs.json", "redaction_report.json")
    )
    assert "sk-test-123456789" not in bundle_text
    assert "not valid json with secret" not in bundle_text
    assert any(link["object_kind"] == "support_bundle" for link in json.loads((bundle_dir / "trace_links.json").read_text(encoding="utf-8"))["links"])


def test_llm_attempt_diagnostics_are_written_only_for_failed_attempts(tmp_path: Path) -> None:
    fixtures = json.loads(VALID_LLM_FIXTURES.read_text(encoding="utf-8"))
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run(
        "analyze_samples",
        {"target_hash": "phase18_llm_success"},
        "phase18_llm_success_test",
    )
    runner = LLMCallRunner(
        SequenceProvider([fixtures["invalid_json"], json.dumps(fixtures["sample_analyses"])]),
        artifact_root=tmp_path / "artifacts",
        state_root=tmp_path / "state",
    )

    result = runner.run(
        "analyze_samples",
        workflow_run_id=run.workflow_run_id,
        analysis_run_id="ana_llm_phase18_success",
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    diagnostic_files = sorted((paths.state_root / "debug" / "llm_attempts" / "ana_llm_phase18_success").glob("*.json"))
    assert result.succeeded
    assert result.attempts_used == 2
    assert len(diagnostic_files) == 1
    diagnostic = json.loads(diagnostic_files[0].read_text(encoding="utf-8"))
    assert diagnostic["attempt_index"] == 1
    assert diagnostic["validation_status"] == "failed"
    assert not any(path.name.startswith("000002_") for path in diagnostic_files)
