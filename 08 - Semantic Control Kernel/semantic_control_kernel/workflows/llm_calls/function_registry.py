from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from semantic_control_kernel.policy.llm_retry_policy import LLMRetryPolicy
from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition


STRUCTURED_JSON = "structured_json"
REPORT_TEXT = "report_text"
LLM_RETRY_POLICY_REF = LLMRetryPolicy().retry_policy_ref


def _definition(row: tuple[str, str, str, str, str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]) -> LLMFunctionDefinition:
    name, call_type, input_contract, output_contract, run_folder, output_path, bindings, consumers, input_paths = row
    return LLMFunctionDefinition(
        llm_function_name=name,
        call_type=call_type,
        input_contract=input_contract,
        output_contract=output_contract,
        run_folder_template=run_folder,
        canonical_output_path=output_path,
        prompt_template_ref=f"phase8.prompts.{name}.v1",
        validator_ref=f"phase8.validators.{name}.v1",
        retry_policy_ref=LLM_RETRY_POLICY_REF,
        downstream_consumers=consumers,
        prompt_bindings=bindings,
        input_artifact_paths=input_paths,
    )


_ROWS: tuple[tuple[str, str, str, str, str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]], ...] = (
    ("analyze_samples", STRUCTURED_JSON, "array[kernel.analyze_sample.input.v1]", "kernel.sample_analyses.v1", "sa/{analysis_run_id}", "sa.json", ("{{kernel_analyze_sample_inputs_json}}",), ("user_report_samples", "create_taxonomy_to_sample_analyses", "create_projections_to_sample_analyses"), ("in/{sample_id}/input.json",)),
    ("user_report_samples", REPORT_TEXT, "kernel.sample_analyses.v1.user_report_samples_seed", "plain_markdown.user_report_samples.v1", "sa/{analysis_run_id}", "report.md", ("{{user_report_samples_seed_json}}",), ("user_review",), ("report.seed.json",)),
    ("create_taxonomy_to_sample_analyses", STRUCTURED_JSON, "kernel.create_taxonomy_to_sample_analyses.input.v1", "kernel.taxonomy_to_sample_analyses.v1", "tax_sa/{analysis_run_id}", "tax_sa.json", ("{{kernel_sample_analyses_v1_json}}",), ("create_taxonomy_update_state",), ("tax_in.json",)),
    ("create_projections_to_sample_analyses", STRUCTURED_JSON, "kernel.create_projections_to_sample_analyses.input.v1", "kernel.projections_to_sample_analyses.v1", "proj_sa/{analysis_run_id}", "proj_sa.json", ("{{kernel_sample_analyses_v1_json}}", "{{kernel_taxonomy_projection_authoring_view_v1_json}}"), ("create_projections_update_state",), ("proj_in.json", "tax_view.json")),
)

_DEFINITIONS = tuple(_definition(row) for row in _ROWS)
LLM_FUNCTION_NAMES = tuple(definition.llm_function_name for definition in _DEFINITIONS)
_REGISTRY: Mapping[str, LLMFunctionDefinition] = MappingProxyType({definition.llm_function_name: definition for definition in _DEFINITIONS})


def get_llm_function_registry() -> Mapping[str, LLMFunctionDefinition]:
    return _REGISTRY


def get_llm_function_definition(llm_function_name: str) -> LLMFunctionDefinition:
    try:
        return _REGISTRY[llm_function_name]
    except KeyError as exc:
        raise KeyError(f"Unknown Phase 8 LLM function: {llm_function_name}") from exc
