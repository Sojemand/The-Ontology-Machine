from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.adapters.llm_adapter import LLMFunctionAdapter
from semantic_control_kernel.types.llm_calls import LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


class AlwaysInvalidProvider(LLMFunctionAdapter):
    def __init__(self, text: str) -> None:
        self.text = text

    def generate(self, request, cancellation=None):
        return LLMProviderResponse(
            provider="fake",
            model=request.model,
            response_id=f"response_{request.attempt_index}",
            status="complete",
            output_text=self.text,
            raw_provider_response_ref={},
            usage={},
            finish_reason="stop",
        )


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_final_validation_failure_mirror_shape_and_event_scoped_tools(tmp_path: Path) -> None:
    fixtures = _fixtures()

    result = LLMCallRunner(AlwaysInvalidProvider(fixtures["invalid_json"]), artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
        preserved_state_summary={"safe_to_retry": True, "resumable_state": True, "cancellable": True},
    )

    assert result.status == "failed_final_validation"
    assert result.final_error is not None
    assert result.final_error.category == "llm_validation"
    assert result.mirror_event["event_type"] == "llm_validation_failed_final"
    assert result.mirror_event["severity"] == "final_error"
    assert result.mirror_event["is_kernel_auto_call"] is True
    assert result.mirror_event["llm_function_name"] == "analyze_samples"
    assert result.mirror_event["attempts_used"] == 3
    assert set(result.mirror_event["allowed_agent_tools"]) == {
        "kernel_retry_recoverable_workflow",
        "kernel_cancel_active_run",
        "kernel_resume_state",
        "kernel_open_support_bundle",
    }
    assert "repair" not in json.dumps(result.mirror_event).lower()
    assert (tmp_path / "sa" / fixtures["analysis_run_id"] / "error.json").is_file()


def test_final_validation_failure_without_preserved_state_exposes_support_only(tmp_path: Path) -> None:
    fixtures = _fixtures()

    result = LLMCallRunner(AlwaysInvalidProvider(fixtures["invalid_json"]), artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
        preserved_state_summary={},
    )

    assert result.status == "failed_final_validation"
    assert result.mirror_event["allowed_agent_tools"] == ["kernel_open_support_bundle"]
    assert result.mirror_event["recovery_options"] == [
        {
            "recovery_id": "support_only",
            "owner": "support_surface",
            "recovery_action_type": "open_support_bundle",
            "agent_tool": "kernel_open_support_bundle",
        },
    ]


def test_final_validation_failure_exposes_bound_recovery_tool_only_when_option_is_bound(tmp_path: Path) -> None:
    fixtures = _fixtures()

    result = LLMCallRunner(AlwaysInvalidProvider(fixtures["invalid_json"]), artifact_root=tmp_path).run(
        "analyze_samples",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["sample_inputs"],
        runtime_settings=fixtures["runtime_settings"],
        preserved_state_summary={
            "bound_recovery_option": {
                "recovery_id": "retry_bound",
                "owner": "kernel",
                "recovery_action_type": "apply_recovery_option",
                "label": "Retry from preserved checkpoint",
            }
        },
    )

    assert result.status == "failed_final_validation"
    assert "kernel_apply_recovery_option" in result.mirror_event["allowed_agent_tools"]
    assert any(
        option["recovery_id"] == "retry_bound" and option["agent_tool"] == "kernel_apply_recovery_option"
        for option in result.mirror_event["recovery_options"]
    )
