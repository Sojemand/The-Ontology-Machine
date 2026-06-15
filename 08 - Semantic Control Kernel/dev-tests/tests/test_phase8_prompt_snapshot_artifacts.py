from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_control_kernel.adapters.llm_adapter import LLMFunctionAdapter
from semantic_control_kernel.types.llm_calls import LLMProviderResponse
from semantic_control_kernel.workflows.llm_calls.function_registry import get_llm_function_registry
from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"

PROMPT_EXPECTATIONS = {
    "analyze_samples": (
        "Analyze them as a set.",
        "Treat candidate codes as one global registry",
        "Codes are semantic identifiers, not local column labels.",
        "create distinct role-scoped codes",
        "promotion candidates as one runtime surface",
        "Return valid JSON only.",
    ),
    "user_report_samples": (
        "Use the same language as the user.",
        "# Sample Analysis Report",
    ),
    "create_taxonomy_to_sample_analyses": (
        "stable machine codes in ASCII snake_case",
        "Promotion slots are taxonomy-defined runtime fields.",
        "Include `other` fallback terms and the exact `fallback_codes` object shown",
    ),
    "create_projections_to_sample_analyses": (
        "Every included code must come from the taxonomy authoring view.",
        "promotion_rules for the projection's taxonomy-defined promotion slots",
    ),
}

OUTPUT_EXPECTATIONS = {
    "analyze_samples": ('"schema_version": "kernel.sample_analyses.v1"', '"projection_seed": {'),
    "user_report_samples": ("- Output structure:", "- `# Sample Analysis Report`"),
    "create_taxonomy_to_sample_analyses": (
        '"schema_version": "kernel.taxonomy_to_sample_analyses.v1"',
        '"taxonomy_core": {',
        '"taxonomy_text": {',
        '"semantic_binding": {',
        "Kernel validation:",
    ),
    "create_projections_to_sample_analyses": ('"schema_version": "kernel.projections_to_sample_analyses.v1"', "Kernel validation:"),
}


OUTPUT_BY_FUNCTION = {
    "analyze_samples": "sample_analyses",
    "user_report_samples": "valid_user_report_samples",
    "create_taxonomy_to_sample_analyses": "taxonomy_to_sample_analyses",
    "create_projections_to_sample_analyses": "projections_to_sample_analyses",
}

INPUT_BY_FUNCTION = {
    "analyze_samples": "sample_inputs",
    "user_report_samples": "sample_analyses",
    "create_taxonomy_to_sample_analyses": "create_taxonomy_input",
    "create_projections_to_sample_analyses": "create_projections_input",
}

MULTI_BINDING_EXPECTATIONS = {
    "create_projections_to_sample_analyses": (
        ("{{kernel_sample_analyses_v1_json}}", "sample_analyses", "proj_in.json"),
        ("{{kernel_taxonomy_projection_authoring_view_v1_json}}", "taxonomy_authoring_view", "tax_view.json"),
    ),
}


class FixtureProvider(LLMFunctionAdapter):
    def __init__(self, fixtures: dict[str, object]) -> None:
        self.fixtures = fixtures

    def generate(self, request, cancellation=None):
        output = self.fixtures[OUTPUT_BY_FUNCTION[request.llm_function_name]]
        text = output if isinstance(output, str) else json.dumps(output)
        return LLMProviderResponse(
            provider="fake",
            model=request.model,
            response_id=f"response_{request.llm_function_name}",
            status="complete",
            output_text=text,
            raw_provider_response_ref={"id": f"raw_{request.llm_function_name}"},
            usage={},
            finish_reason="stop",
        )


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("function_name", tuple(get_llm_function_registry()))
def test_each_llm_function_writes_attempt_and_canonical_artifacts(tmp_path: Path, function_name: str) -> None:
    fixtures = _fixtures()
    definition = get_llm_function_registry()[function_name]

    result = LLMCallRunner(FixtureProvider(fixtures), artifact_root=tmp_path).run(
        function_name,
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures[INPUT_BY_FUNCTION[function_name]],
        runtime_settings=fixtures["runtime_settings"],
    )

    run_dir = tmp_path / definition.run_folder_template.format(analysis_run_id=fixtures["analysis_run_id"])
    assert result.succeeded
    assert (run_dir / "prompt.json").is_file()
    assert (run_dir / "raw.json").is_file()
    assert (run_dir / "a" / "1" / "prompt.json").is_file()
    assert (run_dir / "a" / "1" / "raw.json").is_file()
    assert (run_dir / "a" / "1" / "val.json").is_file()
    assert (run_dir / "a" / "1" / "meta.json").is_file()
    assert (run_dir / definition.canonical_output_path).is_file()
    if definition.call_type == "structured_json":
        assert (run_dir / "a" / "1" / "parsed.json").is_file()
    snapshot_text = (run_dir / "prompt.json").read_text(encoding="utf-8")
    snapshot = json.loads(snapshot_text)
    assert "C:\\Users\\Norma" not in snapshot_text
    assert "old business slots" not in snapshot["prompt"]["user"]
    assert "schema_version" in snapshot_text
    assert "$ref" not in snapshot_text
    assert snapshot["model_request"]["max_output_tokens"] == fixtures["runtime_settings"]["semantic_control_kernel_llm"]["max_output_tokens"]
    for phrase in PROMPT_EXPECTATIONS[function_name]:
        assert phrase in snapshot["prompt"]["user"]
    for phrase in OUTPUT_EXPECTATIONS[function_name]:
        assert phrase in snapshot["prompt"]["user"]


def test_create_taxonomy_prompt_matches_nested_schema_contract(tmp_path: Path) -> None:
    fixtures = _fixtures()
    definition = get_llm_function_registry()["create_taxonomy_to_sample_analyses"]

    LLMCallRunner(FixtureProvider(fixtures), artifact_root=tmp_path).run(
        "create_taxonomy_to_sample_analyses",
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=fixtures["create_taxonomy_input"],
        runtime_settings=fixtures["runtime_settings"],
    )

    run_dir = tmp_path / definition.run_folder_template.format(analysis_run_id=fixtures["analysis_run_id"])
    prompt = json.loads((run_dir / "prompt.json").read_text(encoding="utf-8"))["prompt"]["user"]

    assert '"custom_taxonomy_contract"' not in prompt
    assert '"target": {\n    "update_state_contract": "kernel.create_taxonomy_update_state.input.v1"\n  }' in prompt
    assert '"status": "passed"' in prompt


@pytest.mark.parametrize("function_name", tuple(MULTI_BINDING_EXPECTATIONS))
def test_multi_binding_prompt_artifacts_are_split_by_contract(tmp_path: Path, function_name: str) -> None:
    fixtures = _fixtures()
    definition = get_llm_function_registry()[function_name]
    input_payload = fixtures[INPUT_BY_FUNCTION[function_name]]

    LLMCallRunner(FixtureProvider(fixtures), artifact_root=tmp_path).run(
        function_name,
        workflow_run_id=fixtures["workflow_run_id"],
        analysis_run_id=fixtures["analysis_run_id"],
        input_payload=input_payload,
        runtime_settings=fixtures["runtime_settings"],
    )

    run_dir = tmp_path / definition.run_folder_template.format(analysis_run_id=fixtures["analysis_run_id"])
    snapshot = json.loads((run_dir / "prompt.json").read_text(encoding="utf-8"))
    binding_paths = {binding["name"]: binding["artifact_path"] for binding in snapshot["bindings"]}
    for binding_name, payload_key, expected_file_name in MULTI_BINDING_EXPECTATIONS[function_name]:
        artifact_path = run_dir / expected_file_name
        assert binding_paths[binding_name].endswith(expected_file_name)
        assert json.loads(artifact_path.read_text(encoding="utf-8")) == input_payload[payload_key]
