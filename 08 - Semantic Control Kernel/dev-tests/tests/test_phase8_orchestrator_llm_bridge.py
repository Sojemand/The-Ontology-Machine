from __future__ import annotations

from semantic_control_kernel.adapters.orchestrator_llm import OrchestratorHostedLLMAdapter
from semantic_control_kernel.types.llm_calls import LLMProviderRequest


class FakeOrchestrator:
    def __init__(self) -> None:
        self.profile_payload = None
        self.generate_payload = None

    def kernel_llm_runtime_profile(self, payload):
        self.profile_payload = payload
        return {
            "status": "ok",
            "output_refs": {
                "runtime_settings": {
                    "semantic_control_kernel_llm": {
                        "model": "gpt-test",
                        "max_output_tokens": 8000,
                        "credentials_available": True,
                        "host_capability_available": True,
                    }
                }
            },
        }

    def kernel_llm_generate(self, payload):
        self.generate_payload = payload
        return {
            "status": "ok",
            "output_refs": {
                "llm_response": {
                    "provider": "dummy",
                    "model": "gpt-test",
                    "response_id": "resp_1",
                    "status": "complete",
                    "output_text": '{"ok": true}',
                    "raw_provider_response_ref": {},
                    "usage": {"input_tokens": 1},
                    "finish_reason": "stop",
                }
            },
        }


def test_orchestrator_hosted_llm_adapter_converts_profile_and_generation(tmp_path) -> None:
    fake = FakeOrchestrator()
    adapter = OrchestratorHostedLLMAdapter(state_root=tmp_path, orchestrator_adapter=fake)

    profile = adapter.runtime_profile()
    response = adapter.generate(
        LLMProviderRequest(
            llm_function_name="analyze_samples",
            analysis_run_id="analysis_1",
            attempt_index=1,
            model="gpt-test",
            max_output_tokens=20000,
            response_mode="json_schema",
            messages=({"role": "user", "content": "Return JSON"},),
            target_schema_ref="kernel.sample_analyses.v1",
            target_schema={"type": "object"},
        )
    )

    assert profile["semantic_control_kernel_llm"]["model"] == "gpt-test"
    assert fake.profile_payload["action"] == "kernel_llm_runtime_profile"
    assert fake.generate_payload["action"] == "kernel_llm_generate"
    assert fake.generate_payload["llm_provider_request"]["llm_function_name"] == "analyze_samples"
    assert response.status == "complete"
    assert response.output_text == '{"ok": true}'
    assert response.usage == {"input_tokens": 1}
