"""Tests for successful single-request processing paths."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from llm_interpreter.interpreter import process_single
from llm_interpreter.models import InterpreterConfig
from tests.support.provider_stubs import MockProvider


def test_happy_path_writes_structured_output(sample_request_file, sample_llm_output, tmp_path):
    provider = MockProvider(response_json=sample_llm_output)
    output_path = tmp_path / "output" / "scan.pdf.structured.json"
    result = process_single(sample_request_file, output_path, InterpreterConfig(), provider)
    assert result["status"] == "ok"
    out_path = Path(result["output_path"])
    output = json.loads(out_path.read_text(encoding="utf-8"))
    assert out_path.name == "scan.pdf.structured.json"
    assert output["schema_version"] == "1.0"
    assert output["processing"]["interpreter_profile"] == "vision"
    assert output["processing"]["provider"] == "openai"
    assert output["processing"]["model"] == "gpt-5.4"
    assert output["content"]["rows"][0]["_source_refs"]["betrag"] == "page1_para_2"
    assert output["content"]["segments"][0]["segment_id"] == "Page1_Segment1"
    assert output["content"]["segments"][0]["function"] == "document_heading"
    assert output["content"]["free_text"].startswith("Beitragsrechnung 2026")
    assert provider.calls[0]["thinking_effort"] == "none"
    assert result["needs_review"] is False


def test_missing_free_text_marks_review(sample_request_file, sample_llm_output, tmp_path):
    output = copy.deepcopy(sample_llm_output)
    output["content"]["free_text"] = None
    result = process_single(
        sample_request_file,
        tmp_path / "output" / "doc.structured.json",
        InterpreterConfig(),
        MockProvider(response_json=output),
    )
    saved = json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert saved["processing"]["needs_review"] is False
    assert saved["processing"]["review_reason"] is None


def test_conflicting_source_refs_no_longer_change_vision_output(sample_request_file, sample_llm_output, tmp_path):
    output = copy.deepcopy(sample_llm_output)
    output["content"]["rows"][0]["betrag"] = 999.0
    result = process_single(
        sample_request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        InterpreterConfig(),
        MockProvider(response_json=output),
    )
    saved = json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert saved["processing"]["needs_review"] is False
    assert saved["content"]["rows"][0]["_source_refs"]["betrag"] == "page1_para_2"


def test_segment_source_refs_are_stripped_if_a_model_still_sends_them(sample_request_file, sample_llm_output, tmp_path):
    output = copy.deepcopy(sample_llm_output)
    output["content"]["segments"][0]["_source_refs"] = {"text": "page1_para_1"}

    result = process_single(
        sample_request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        InterpreterConfig(),
        MockProvider(response_json=output),
    )

    saved = json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert "_source_refs" not in saved["content"]["segments"][0]


def test_vision_only_values_remain_without_source_refs(sample_request_file, sample_llm_output, tmp_path):
    output = copy.deepcopy(sample_llm_output)
    output["content"]["rows"][0].pop("_source_refs")
    output["content"]["rows"][0]["due_date"] = "2026-04-15"
    result = process_single(
        sample_request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        InterpreterConfig(),
        MockProvider(response_json=output),
    )
    saved = json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))
    assert saved["content"]["rows"][0]["due_date"] == "2026-04-15"
    assert "_source_refs" not in saved["content"]["rows"][0]


def test_fixed_no_thinking_is_forwarded(sample_request_file, sample_llm_output, tmp_path):
    config = InterpreterConfig()
    provider = MockProvider(response_json=sample_llm_output)
    process_single(sample_request_file, tmp_path / "output" / "scan.pdf.structured.json", config, provider)
    assert provider.calls[0]["thinking_effort"] == "none"


def test_dict_input_is_not_mutated(sample_request, sample_llm_output, tmp_path):
    original = copy.deepcopy(sample_request)
    result = process_single(
        sample_request,
        tmp_path / "output" / "scan.pdf.structured.json",
        InterpreterConfig(),
        MockProvider(response_json=sample_llm_output),
    )
    assert result["status"] == "ok"
    assert sample_request == original


def test_weird_usage_payload_does_not_crash_cost_estimation(sample_request_file, sample_llm_output, tmp_path):
    class WeirdUsageProvider(MockProvider):
        def __init__(self):
            super().__init__(response_json=sample_llm_output)
            self._last_usage = {"input_tokens": "1.5", "output_tokens": "2"}
            self._last_model = "gpt-5"

    result = process_single(
        sample_request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        InterpreterConfig(),
        WeirdUsageProvider(),
    )
    assert result["status"] == "ok"
    assert result["cost_estimate_usd"] is not None
