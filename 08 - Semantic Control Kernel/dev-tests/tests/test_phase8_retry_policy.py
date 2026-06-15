from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from semantic_control_kernel.adapters.llm_adapter import LLMFunctionAdapter
from semantic_control_kernel.types.llm_calls import LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


class SequenceProvider(LLMFunctionAdapter):
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.requests = []

    def generate(self, request, cancellation=None):
        self.requests.append(request)
        index = len(self.requests) - 1
        return LLMProviderResponse(
            provider="fake",
            model=request.model,
            response_id=f"response_{len(self.requests)}",
            status="complete",
            output_text=self.outputs[index],
            raw_provider_response_ref={},
            usage={},
            finish_reason="stop",
        )


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_validation_failures_retry_three_attempts_with_compact_feedback(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = SequenceProvider(
        [
            fixtures["invalid_json"],
            fixtures["markdown_wrapped_json"],
            json.dumps(fixtures["sample_analyses"]),
        ]
    )

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    assert result.succeeded
    assert result.attempts_used == 3
    assert len(result.retry_events) == 2
    assert all("repair JSON" not in event.get("validation_error_summary", "") for event in result.retry_events)
    assert provider.requests[0].target_schema_ref == provider.requests[1].target_schema_ref == provider.requests[2].target_schema_ref
    assert provider.requests[0].analysis_run_id == provider.requests[1].analysis_run_id == provider.requests[2].analysis_run_id


def test_failed_attempts_are_not_canonical_downstream_outputs(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = SequenceProvider([fixtures["invalid_json"], json.dumps(fixtures["sample_analyses"])])

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    run_dir = tmp_path / "sa" / fixtures["analysis_run_id"]
    assert result.succeeded
    assert (run_dir / "a" / "1" / "val.json").is_file()
    assert json.loads((run_dir / "sa.json").read_text(encoding="utf-8")) == fixtures["sample_analyses"]


def test_repairable_sample_analysis_shape_does_not_trigger_retry(tmp_path: Path) -> None:
    fixtures = _fixtures()
    relaxed = deepcopy(fixtures["sample_analyses"])
    del relaxed["taxonomy_seed"]["candidate_codes"]
    del relaxed["projection_seed"]["candidate_projection_ids"]
    del relaxed["projection_seed"]["projections"][0]["status"]
    del relaxed["user_report_samples_seed"]["overview"]
    relaxed["projection_seed"]["projections"][0]["status"] = "candidate"
    relaxed["sample_set"]["ignored_extra"] = "kept only in raw provider output"
    provider = SequenceProvider([json.dumps(relaxed)])

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    assert result.succeeded
    assert len(provider.requests) == 1
    assert result.output["taxonomy_seed"]["candidate_codes"]
    assert result.output["projection_seed"]["candidate_projection_ids"] == ["finance.default.v1"]
    assert result.output["projection_seed"]["projections"][0]["status"] == "draft"
    assert result.output["user_report_samples_seed"]["overview"]
    assert "ignored_extra" not in result.output["sample_set"]
