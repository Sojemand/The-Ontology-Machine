from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_control_kernel.workflows.llm_calls.function_registry import (
    REPORT_TEXT,
    get_llm_function_registry,
)
from semantic_control_kernel.workflows.llm_calls.output_schemas import (
    build_output_schema,
    output_schema_name,
    schema_supports_strict,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"

INPUT_BY_FUNCTION = {
    "analyze_samples": "sample_inputs",
    "user_report_samples": "sample_analyses",
    "create_taxonomy_to_sample_analyses": "create_taxonomy_input",
    "create_projections_to_sample_analyses": "create_projections_input",
}


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("function_name", tuple(get_llm_function_registry()))
def test_structured_llm_functions_have_openai_strict_output_schemas(function_name: str) -> None:
    fixtures = _fixtures()
    definition = get_llm_function_registry()[function_name]
    schema = build_output_schema(definition, fixtures[INPUT_BY_FUNCTION[function_name]])

    if definition.call_type == REPORT_TEXT:
        assert schema is None
        return

    assert schema is not None
    assert output_schema_name(definition).startswith("kernel_")
    assert schema_supports_strict(schema)
    assert "$ref" not in json.dumps(schema)
