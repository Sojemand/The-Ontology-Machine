from __future__ import annotations

from orchestrator.integrations import EmbeddingStageResult, NormalizationStageResult, adapter, policy


def test_parse_extraction_result_coerces_string_lists_without_character_splitting() -> None:
    result = adapter.parse_extraction_result(
        {
            "status": "ok",
            "document_raw_path": "document.raw.json",
            "page_raw_paths": "page.raw.json",
            "page_asset_paths": "page.png",
        }
    )

    assert result.document_raw_path == "document.raw.json"
    assert result.page_raw_paths == ["page.raw.json"]
    assert result.page_asset_paths == ["page.png"]


def test_parse_embedding_result_coerces_invalid_count_to_zero() -> None:
    result = adapter.parse_embedding_result({"status": "completed", "count": "NaN", "reason": "done"})

    assert result == EmbeddingStageResult(status="completed", count=0, reason="done")


def test_parse_contract_results_coerce_null_strings_to_empty() -> None:
    interpretation = adapter.parse_interpretation_result(
        {"status": "ok", "structured_path": None, "debug_bundle_path": None, "review_reason": None}
    )
    validation_result = adapter.parse_validation_result({"status": "PASS", "report_path": None, "detail": None})
    normalization = adapter.parse_normalization_result(
        {"status": "OK", "output_path": None, "message": None, "review_reason": None}
    )
    corpus = adapter.parse_corpus_load_result({"status": "loaded", "reason": None})
    embeddings = adapter.parse_embedding_result({"status": "completed", "count": 1, "reason": None})

    assert interpretation.structured_path == ""
    assert interpretation.debug_bundle_path == ""
    assert interpretation.review_reason == ""
    assert validation_result.report_path == ""
    assert validation_result.detail == ""
    assert normalization == NormalizationStageResult(
        status="OK",
        output_path="",
        needs_review=False,
        message="",
        review_reason="",
        error="",
    )
    assert corpus.reason == ""
    assert embeddings.reason == ""


def test_parse_dependency_statuses_accepts_legacy_status_ok() -> None:
    dependencies = adapter.parse_dependency_statuses({"dependencies": [{"name": "config", "status": "ok"}]})

    assert len(dependencies) == 1
    assert dependencies[0].name == "config"
    assert dependencies[0].required is True
    assert dependencies[0].healthy is True


def test_policy_coercers_cover_bool_int_and_string_list_inputs() -> None:
    values = sorted(policy.coerce_contract_str_list({"a", "b"}))

    assert policy.coerce_contract_bool("yes") is True
    assert policy.coerce_contract_bool("off", True) is False
    assert policy.coerce_contract_bool("unknown", True) is True
    assert policy.coerce_contract_int("NaN", 7) == 7
    assert policy.coerce_contract_str(None, "fallback") == "fallback"
    assert values == ["a", "b"]
