from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.adapters.llm_adapter import LLMFunctionAdapter
from semantic_control_kernel.types.llm_calls import LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


class SecretInvalidProvider(LLMFunctionAdapter):
    def generate(self, request, cancellation=None):
        return LLMProviderResponse(
            provider="fake",
            model=request.model,
            response_id=f"response_{request.attempt_index}",
            status="complete",
            output_text="not json secret-token",
            raw_provider_response_ref={
                "authorization": "Bearer secret-token",
                "body": "full raw body secret-token"
            },
            usage={},
            finish_reason="stop",
        )


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_support_bundle_refs_exist_and_user_agent_summary_redacts_raw_bodies(tmp_path: Path) -> None:
    fixtures = _fixtures()

    result = LLMCallRunner(SecretInvalidProvider(), artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
    )

    support_ref = result.mirror_event["support_bundle_ref"]
    support_path = tmp_path / support_ref["artifact_path"]
    assert support_path.is_file()
    support_text = support_path.read_text(encoding="utf-8")
    mirror_text = json.dumps(result.mirror_event)
    assert "secret-token" not in support_text
    assert "secret-token" not in mirror_text
    assert "full raw body" not in support_text
    assert "llm_response_ref" in mirror_text
