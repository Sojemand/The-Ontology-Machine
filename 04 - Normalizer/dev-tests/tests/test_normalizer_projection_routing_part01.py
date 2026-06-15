from tests.normalizer_projection_routing_shared import *  # noqa: F401,F403

def test_build_prompt_preview_uses_projection_hint_profile(tmp_project_root, sample_structured_file):
    payload = json.loads(sample_structured_file.read_text(encoding="utf-8"))
    apply_operations_raw_signals(payload)
    payload["context"]["projection_hint"] = {
        "projection_id": "operations.default.v1",
        "confidence": 0.88,
        "reason": "Logistics and execution-plan signals in the interpreter.",
        "matched_signals": ["delivery note", "transport order"],
    }
    sample_structured_file.write_text(json.dumps(payload), encoding="utf-8")

    _system_prompt, user_prompt = DocumentNormalizer(tmp_project_root, load_config(tmp_project_root)).build_prompt_preview(sample_structured_file)
    assert "Active taxonomy profile: operations.default.v1" in user_prompt

def test_normalize_uses_valid_projection_hint_to_override_fallback_profile(
    tmp_project_root,
    sample_structured_file,
    normalizer_runtime_settings,
):
    payload = json.loads(sample_structured_file.read_text(encoding="utf-8"))
    apply_operations_raw_signals(payload)
    payload["context"]["projection_hint"] = {
        "projection_id": "operations.default.v1",
        "confidence": 0.88,
        "reason": "Logistics and execution-plan signals in the interpreter.",
        "matched_signals": ["delivery note", "transport order"],
    }
    sample_structured_file.write_text(json.dumps(payload), encoding="utf-8")

    hinted_output = operations_output(
        document_type="delivery_note",
        category="operations",
        subcategory="logistics",
        document_title="Transport order / delivery note",
        description="Transport of several machines.",
        fields={"transport_order_number": "BK-20220771 - outbound"},
        rows=[{"_row_type": "line_item", "position": 1, "quantity": "4", "description": "Euro pallets"}],
    )

    class HintProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(hinted_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=HintProvider(),
    ).normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )

    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["context"]["taxonomy_profile_id"] == "operations.default.v1"
    assert output_data["projection"]["selection"]["mode"] == "hint_validated"
    assert output_data["projection"]["selection"]["hint_projection_id"] == "operations.default.v1"

def test_normalize_batch_can_resolve_different_projections_per_document(
    tmp_project_root,
    sample_batch_dir,
    sample_structured_input,
    sample_model_output,
    normalizer_runtime_settings,
):
    operations_path = sample_batch_dir / "sample_1.pdf.structured.json"
    operations_payload = json.loads(json.dumps(sample_structured_input))
    apply_operations_raw_signals(operations_payload)
    operations_payload["context"]["projection_hint"] = {
        "projection_id": "operations.default.v1",
        "confidence": 0.91,
        "reason": "Logistics document in the interpreter.",
        "matched_signals": ["delivery note", "logistics"],
    }
    operations_path.write_text(json.dumps(operations_payload), encoding="utf-8")

    class MixedProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            if "Active taxonomy profile: operations.default.v1" in messages[1]["content"]:
                return json.dumps(
                    operations_output(
                        document_type="delivery_note",
                        category="operations",
                        subcategory="logistics",
                        document_title="Transport order / delivery note",
                        description="Transport of several machines.",
                        fields={"transport_order_number": "BK-20220771 - outbound"},
                        rows=[{"_row_type": "line_item", "position": 1, "quantity": "4", "description": "Euro pallets"}],
                    )
                )
            return json.dumps({**sample_model_output, "context": {**sample_model_output["context"]}, "content": {**sample_model_output["content"]}})

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    results = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=MixedProvider(),
    ).normalize_batch(
        sample_batch_dir,
        tmp_project_root / "output",
        workers=2,
    )

    outputs = {Path(result.output_path).name: json.loads(Path(result.output_path).read_text(encoding="utf-8")) for result in results}
    assert outputs["sample_0.pdf.structured.normalized.json"]["context"]["taxonomy_profile_id"] == "housing.default.v1"
    assert outputs["sample_1.pdf.structured.normalized.json"]["context"]["taxonomy_profile_id"] == "operations.default.v1"
