from tests.normalizer_projection_routing_shared import *  # noqa: F401,F403

def test_preview_single_and_batch_use_identical_projection_arbitration(
    tmp_project_root,
    sample_structured_file,
    sample_batch_dir,
    normalizer_runtime_settings,
):
    payload = json.loads(sample_structured_file.read_text(encoding="utf-8"))
    apply_operations_raw_signals(payload)
    payload["context"]["projection_hint"] = {
        "projection_id": "operations.default.v1",
        "confidence": 0.9,
        "reason": "Logistics document in the interpreter.",
        "matched_signals": ["delivery note", "transport order"],
    }
    sample_structured_file.write_text(json.dumps(payload), encoding="utf-8")
    for file_path in sample_batch_dir.glob("*.structured.json"):
        file_path.write_text(json.dumps(payload), encoding="utf-8")

    expected_selection = resolve_projection(
        project_root=tmp_project_root,
        fallback_profile=load_local_profile(tmp_project_root, "housing.default.v1"),
        raw_doc=payload,
        hint_mode=load_config(tmp_project_root).projection_hint_mode,
    )
    hinted_output = operations_output(
        document_type="delivery_note",
        category="operations",
        subcategory="logistics",
        document_title="Transport order / delivery note",
        description="Transport of several machines.",
        fields={"transport_order_number": "BK-20220771 - outbound"},
        rows=[{"_row_type": "line_item", "position": 1, "quantity": "4", "description": "Euro pallets"}],
    )

    class StableOperationsProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(hinted_output)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=StableOperationsProvider(),
    )
    _system_prompt, user_prompt = normalizer.build_prompt_preview(sample_structured_file)
    single_result = normalizer.normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )
    batch_results = normalizer.normalize_batch(sample_batch_dir, tmp_project_root / "output", workers=2)

    assert f"Active taxonomy profile: {expected_selection.profile.projection_id}" in user_prompt
    single_output = json.loads(Path(single_result.output_path).read_text(encoding="utf-8"))
    assert single_output["projection"]["selection"] == expected_selection.to_dict()
    for result in batch_results:
        batch_output = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
        assert batch_output["projection"]["selection"] == expected_selection.to_dict()

def test_release_runtime_can_normalize_without_compiled_flat_taxonomy_assets(
    tmp_project_root,
    sample_structured_file,
    normalizer_runtime_settings,
):
    release = build_semantic_release(tmp_project_root)
    for path in sorted((tmp_project_root / "config").glob("normalizer_taxonomy.*.json")):
        path.unlink()

    class ReleaseProvider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(
                {
                    "processing": {
                        "model_confidence": 0.9,
                        "needs_review": False,
                        "review_reason": None,
                        "vision_used": False,
                    },
                    "context": {"document_title": "Housing utility cost statement"},
                    "classification": {
                        "document_type": "utility_bill",
                        "category": "housing",
                        "subcategory": "utility_costs",
                    },
                    "content": {
                        "free_text": "Housing utility cost statement with cost items and payment context.",
                        "fields": {},
                        "rows": [],
                    },
                    "relations": [],
                }
            )

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    normalizer = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=ReleaseProvider(),
        semantic_release=release,
    )

    _system_prompt, user_prompt = normalizer.build_prompt_preview(sample_structured_file)
    result = normalizer.normalize(
        sample_structured_file,
        _normalized_output_path(tmp_project_root, sample_structured_file),
    )
    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))

    assert "Active taxonomy profile: housing.default.v1" in user_prompt
    assert output_data["context"]["taxonomy_profile_id"] == "housing.default.v1"
    assert output_data["projection"]["selection"]["catalog_version"].startswith("sha256:")
