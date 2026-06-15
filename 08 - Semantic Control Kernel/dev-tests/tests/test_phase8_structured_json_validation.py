from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from semantic_control_kernel.workflows.llm_calls.function_registry import get_llm_function_definition
from semantic_control_kernel.validation.llm_validation import (
    derive_validation_context,
    validate_structured_output,
    validate_structured_output_text,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_fixture_bundle_is_self_contained_and_ref_free() -> None:
    fixtures = _fixtures()

    assert fixtures["workflow_run_id"]
    assert "$ref" not in json.dumps(fixtures)


def test_valid_structured_outputs_pass_for_active_llm_functions() -> None:
    fixtures = _fixtures()
    cases = (
        ("analyze_samples", "sample_analyses", "sample_inputs"),
        ("create_taxonomy_to_sample_analyses", "taxonomy_to_sample_analyses", "create_taxonomy_input"),
        ("create_projections_to_sample_analyses", "projections_to_sample_analyses", "create_projections_input"),
    )

    for function_name, output_key, input_key in cases:
        definition = get_llm_function_definition(function_name)
        context = derive_validation_context(definition, fixtures[input_key])
        assert validate_structured_output(fixtures[output_key], definition=definition, context=context).passed


def test_invalid_json_and_markdown_wrapped_json_are_rejected() -> None:
    definition = get_llm_function_definition("analyze_samples")

    _parsed, invalid = validate_structured_output_text(output_text="not-json", definition=definition)
    _parsed, markdown = validate_structured_output_text(output_text="```json\n{}\n```", definition=definition)

    assert "invalid_json" in invalid.error_codes
    assert "markdown_outside_json" in markdown.error_codes


def test_schema_unknown_field_enum_fingerprint_and_sample_mismatches_fail() -> None:
    fixtures = _fixtures()
    definition = get_llm_function_definition("analyze_samples")
    context = derive_validation_context(definition, fixtures["sample_inputs"])

    schema_mismatch = deepcopy(fixtures["sample_analyses"])
    schema_mismatch["schema_version"] = "kernel.taxonomy_to_sample_analyses.v1"
    assert "schema_version_mismatch" in validate_structured_output(schema_mismatch, definition=definition).error_codes

    unknown = deepcopy(fixtures["sample_analyses"])
    unknown["unexpected"] = True
    assert validate_structured_output(unknown, definition=definition, context=context).passed

    enum = deepcopy(fixtures["sample_analyses"])
    enum["analysis_scope"] = "wrong"
    assert "enum_mismatch" in validate_structured_output(enum, definition=definition).error_codes

    sample_mismatch = deepcopy(fixtures["sample_analyses"])
    sample_mismatch["sample_set"]["sample_ids"] = ["different"]
    assert "sample_id_mismatch" in validate_structured_output(sample_mismatch, definition=definition, context=context).error_codes

    bad_candidate_code = deepcopy(fixtures["sample_analyses"])
    bad_candidate_code["taxonomy_seed"]["candidate_codes"] = ["Bad-Code"]
    assert "function_rule_violation" in validate_structured_output(bad_candidate_code, definition=definition, context=context).error_codes

    bad_projection_id = deepcopy(fixtures["sample_analyses"])
    bad_projection_id["projection_seed"]["candidate_projection_ids"] = ["Bad Projection"]
    assert "unknown_projection_id" in validate_structured_output(bad_projection_id, definition=definition, context=context).error_codes


def test_dynamic_promotion_slot_registry_rejects_bad_slot_definitions_and_unknown_bindings() -> None:
    fixtures = _fixtures()
    definition = get_llm_function_definition("create_taxonomy_to_sample_analyses")
    context = derive_validation_context(definition, fixtures["create_taxonomy_input"])

    bad_slot = deepcopy(fixtures["taxonomy_to_sample_analyses"])
    bad_slot["taxonomy_proposal"]["taxonomy_core"]["promotion_slots"][0]["cardinality"] = "manyish"
    assert "enum_mismatch" in validate_structured_output(bad_slot, definition=definition, context=context).error_codes

    bad_binding = deepcopy(fixtures["taxonomy_to_sample_analyses"])
    bad_binding["taxonomy_proposal"]["semantic_binding"]["field_codes"][0]["promotion_slot"] = "missing_slot"
    assert "function_rule_violation" in validate_structured_output(bad_binding, definition=definition, context=context).error_codes


def test_projection_validation_blocks_when_prompt_has_no_promotion_slot_registry() -> None:
    fixtures = _fixtures()
    definition = get_llm_function_definition("create_projections_to_sample_analyses")
    input_payload = deepcopy(fixtures["create_projections_input"])
    input_payload["taxonomy_authoring_view"]["promotion_slots"] = []
    context = derive_validation_context(definition, input_payload)

    invalid = deepcopy(fixtures["projections_to_sample_analyses"])
    invalid["projection_proposals"][0]["promotion_rules"] = [{"slot": "invoice_total", "source_paths": ["fields.total"]}]

    assert "function_rule_violation" in validate_structured_output(invalid, definition=definition, context=context).error_codes


def test_projection_validation_rejects_empty_promotion_source_paths() -> None:
    fixtures = _fixtures()
    definition = get_llm_function_definition("create_projections_to_sample_analyses")
    context = derive_validation_context(definition, fixtures["create_projections_input"])

    invalid = deepcopy(fixtures["projections_to_sample_analyses"])
    invalid["projection_proposals"][0]["promotion_rules"].append(
        {"slot": "amount_due", "source_paths": []}
    )

    assert "invalid_promotion_path" in validate_structured_output(invalid, definition=definition, context=context).error_codes


def test_analyze_samples_tolerates_unknown_fields_before_local_target_schema() -> None:
    fixtures = _fixtures()
    definition = get_llm_function_definition("analyze_samples")
    output = deepcopy(fixtures["sample_analyses"])
    output["extra_owner_hint"] = "ignored"

    assert validate_structured_output(output, definition=definition).passed
