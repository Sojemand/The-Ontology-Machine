from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.adapters.llm_adapter import LLMFunctionAdapter
from semantic_control_kernel.types.llm_calls import CancellationToken, LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


class StatusProvider(LLMFunctionAdapter):
    def __init__(self, statuses: list[str], final_output: dict[str, object] | None = None, error_message: str | None = None) -> None:
        self.statuses = statuses
        self.final_output = final_output
        self.error_message = error_message
        self.calls = 0

    def generate(self, request, cancellation=None):
        self.calls += 1
        status = self.statuses[min(self.calls - 1, len(self.statuses) - 1)]
        if status == "complete":
            text = json.dumps(self.final_output)
        else:
            text = ""
        return LLMProviderResponse(
            provider="fake",
            model=request.model,
            response_id=f"response_{self.calls}",
            status=status,
            output_text=text,
            raw_provider_response_ref={"status": status},
            usage={},
            finish_reason="stop",
            error_code=status if status != "complete" else None,
            error_message=self.error_message if status != "complete" else None,
        )


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_timeout_rate_limit_and_5xx_like_errors_retry(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = StatusProvider(["timeout", "rate_limit", "complete"], fixtures["sample_analyses"])

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    assert result.succeeded
    assert provider.calls == 3


def test_incomplete_read_provider_error_retries(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = StatusProvider(
        ["provider_error", "complete"],
        fixtures["sample_analyses"],
        error_message="IncompleteRead(1023196 bytes read)",
    )

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    assert result.succeeded
    assert provider.calls == 2
    first_metadata = json.loads(
        (
            tmp_path
            / "sa"
            / fixtures["analysis_run_id"]
            / "a"
            / "1"
            / "meta.json"
        ).read_text(encoding="utf-8")
    )
    assert first_metadata["next_action"] == "retry_provider_transient_failure"


def test_auth_runtime_blocker_fails_closed_without_validation_final(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = StatusProvider(["auth_missing"])

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    assert result.status == "failed_provider"
    assert result.mirror_event["event_type"] == "pipeline_error"
    assert result.final_error.category == "llm_provider"


def test_non_transient_provider_failure_preserves_owner_error_message(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = StatusProvider(["provider_error"], error_message="Provider rejected request")

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    assert result.status == "failed_provider"
    assert provider.calls == 1
    assert "Provider rejected request" in result.final_error.validation_error_summary
    raw_path = tmp_path / "sa" / fixtures["analysis_run_id"] / "a" / "1" / "raw.json"
    assert json.loads(raw_path.read_text(encoding="utf-8"))["error_message"] == "Provider rejected request"


def test_cancellation_does_not_emit_final_llm_validation_failure(tmp_path: Path) -> None:
    fixtures = _fixtures()
    token = CancellationToken()
    token.cancel()
    provider = StatusProvider(["complete"], fixtures["sample_analyses"])

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
        cancellation=token,
    )

    assert result.status == "cancelled"
    assert provider.calls == 0
    assert result.mirror_event["event_type"] == "workflow_cancelled"
