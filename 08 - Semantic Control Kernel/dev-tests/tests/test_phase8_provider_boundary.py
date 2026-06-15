from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_control_kernel.adapters.llm_adapter import (
    LLMCredentialsMissingError,
    LLMFunctionAdapter,
    LLMRuntimeMissingError,
)
from semantic_control_kernel.types.llm_calls import LLMProviderRequest, LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


class FakeProvider(LLMFunctionAdapter):
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.requests: list[LLMProviderRequest] = []

    def generate(self, request, cancellation=None):
        self.requests.append(request)
        return LLMProviderResponse(
            provider="fake",
            model=request.model,
            response_id=f"response_{len(self.requests)}",
            status="complete",
            output_text=json.dumps(self.output),
            raw_provider_response_ref={"body": self.output, "authorization": "Bearer secret-token"},
            usage={"output_tokens": 10},
            finish_reason="stop",
        )


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_runner_calls_only_llm_function_adapter_port(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = FakeProvider(fixtures["sample_analyses"])

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    assert result.succeeded
    assert len(provider.requests) == 1
    assert provider.requests[0].llm_function_name == "analyze_samples"
    assert provider.requests[0].response_mode == "json_schema"
    assert provider.requests[0].max_output_tokens == fixtures["runtime_settings"]["semantic_control_kernel_llm"]["max_output_tokens"]
    assert provider.requests[0].target_schema_name == "kernel_analyze_samples_output"
    assert provider.requests[0].target_schema_sha256
    assert provider.requests[0].target_schema is not None


def test_missing_kernel_runtime_profile_blocks_before_provider_execution(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = FakeProvider(fixtures["sample_analyses"])

    with pytest.raises(LLMRuntimeMissingError):
        LLMCallRunner(provider, artifact_root=tmp_path).run(
            "analyze_samples",
            workflow_run_id=fixtures["workflow_run_id"],
            analysis_run_id=fixtures["analysis_run_id"],
            input_payload=fixtures["sample_inputs"],
            runtime_settings=None,
        )

    assert provider.requests == []


def test_interpreter_runtime_profile_is_not_used_as_fallback(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = FakeProvider(fixtures["sample_analyses"])

    with pytest.raises(LLMRuntimeMissingError):
        LLMCallRunner(provider, artifact_root=tmp_path).run(
            "analyze_samples",
            workflow_run_id=fixtures["workflow_run_id"],
            analysis_run_id=fixtures["analysis_run_id"],
            input_payload=fixtures["sample_inputs"],
            runtime_settings={"interpreter": {"model": "wrong", "max_output_tokens": 1}},
        )

    assert provider.requests == []


def test_flat_runtime_settings_do_not_bypass_kernel_profile_boundary(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = FakeProvider(fixtures["sample_analyses"])

    with pytest.raises(LLMRuntimeMissingError):
        LLMCallRunner(provider, artifact_root=tmp_path).run(
            "analyze_samples",
            workflow_run_id=fixtures["workflow_run_id"],
            analysis_run_id=fixtures["analysis_run_id"],
            input_payload=fixtures["sample_inputs"],
            runtime_settings={"model": "flat-bypass", "max_output_tokens": 20000},
        )

    assert provider.requests == []


def test_missing_credentials_flag_blocks_before_provider_execution(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = FakeProvider(fixtures["sample_analyses"])
    runtime = dict(fixtures["runtime_settings"]["semantic_control_kernel_llm"])
    runtime["credentials_available"] = False

    with pytest.raises(LLMCredentialsMissingError):
        LLMCallRunner(provider, artifact_root=tmp_path).run(
            "analyze_samples",
            workflow_run_id=fixtures["workflow_run_id"],
            analysis_run_id=fixtures["analysis_run_id"],
            input_payload=fixtures["sample_inputs"],
            runtime_settings={"semantic_control_kernel_llm": runtime},
        )

    assert provider.requests == []


def test_kernel_runtime_uses_owner_output_budget(tmp_path: Path) -> None:
    fixtures = _fixtures()
    provider = FakeProvider(fixtures["sample_analyses"])
    runtime = dict(fixtures["runtime_settings"]["semantic_control_kernel_llm"])
    runtime["max_output_tokens"] = 1

    result = LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings={"semantic_control_kernel_llm": runtime},
    )

    assert result.succeeded
    assert provider.requests[0].max_output_tokens == 1


def test_secrets_never_appear_in_request_or_artifacts(tmp_path: Path) -> None:
    fixtures = _fixtures()
    secret_input = dict(fixtures["sample_inputs"][0])
    secret_input["api_key"] = "secret-api-key"
    provider = FakeProvider(fixtures["sample_analyses"])

    LLMCallRunner(provider, artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=[secret_input],
        runtime_settings=fixtures["runtime_settings"],
    )

    assert "secret-api-key" not in json.dumps(provider.requests[0].to_dict())
    for path in tmp_path.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "secret-api-key" not in text
        assert "secret-token" not in text
