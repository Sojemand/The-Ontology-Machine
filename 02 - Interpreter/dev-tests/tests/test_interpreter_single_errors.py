"""Tests for structured single-request error handling."""
from __future__ import annotations

import copy
import json
from unittest.mock import patch

from llm_interpreter.interpreter import process_single
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.providers import ProviderError
from tests.support.provider_stubs import MockProvider


def test_missing_page_asset_fails_fast(sample_request, tmp_path):
    request = copy.deepcopy(sample_request)
    request["page_assets"][0]["path"] = str(tmp_path / "page_assets" / "missing.png")
    input_file = tmp_path / "requests" / "bad.request.json"
    input_file.parent.mkdir(parents=True, exist_ok=True)
    input_file.write_text(json.dumps(request), encoding="utf-8")
    result = process_single(input_file, tmp_path / "output" / "bad.structured.json", InterpreterConfig(), MockProvider(response_json={}))
    assert result["status"] == "error"
    assert "Seitenbild fehlt" in result["error"]


def test_invalid_request_page_count_returns_structured_error(sample_request, tmp_path):
    request = copy.deepcopy(sample_request)
    request["source"]["page_count"] = "two"
    result = process_single(request, tmp_path / "output" / "bad.structured.json", InterpreterConfig(), MockProvider(response_json={}))
    assert result["status"] == "error"
    assert "source.page_count" in result["error"]


def test_write_error_returns_structured_result(sample_request_file, sample_llm_output, tmp_path):
    with patch("llm_interpreter.interpreter.atomic_json_write", side_effect=OSError("disk full")):
        result = process_single(
            sample_request_file,
            tmp_path / "output" / "scan.pdf.structured.json",
            InterpreterConfig(),
            MockProvider(response_json=sample_llm_output),
        )
    assert result["status"] == "error"
    assert "disk full" in result["error"]


def test_invalid_json_response_returns_structured_error(sample_request_file, tmp_path):
    result = process_single(
        sample_request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        InterpreterConfig(),
        MockProvider(response_text="definitely not json"),
    )
    assert result["status"] == "error"
    assert "JSON-Parse-Fehler" in result["error"]


def test_empty_llm_response_returns_error(sample_request_file, tmp_path):
    class EmptyProvider:
        provider_name = "openai"
        _last_usage = {}
        _last_model = "gpt-5.4"

        def generate(self, **_kwargs):
            return ""

    result = process_single(
        sample_request_file,
        tmp_path / "output" / "scan.pdf.structured.json",
        InterpreterConfig(),
        EmptyProvider(),
    )
    assert result["status"] == "error"
    assert "LLM-Antwort leer" in result["error"]


def test_provider_factory_errors_are_returned_structurally(sample_request_file, tmp_path):
    with patch("llm_interpreter.interpreter.create_provider", side_effect=ProviderError("VISION_PROVIDER_API_KEY nicht gesetzt")):
        result = process_single(sample_request_file, tmp_path / "output" / "scan.pdf.structured.json", InterpreterConfig(), provider=None)
    assert result["status"] == "error"
    assert "VISION_PROVIDER_API_KEY nicht gesetzt" in result["error"]


def test_malformed_processing_container_returns_structured_error(sample_request_file, sample_llm_output, tmp_path):
    output = copy.deepcopy(sample_llm_output)
    output["processing"] = []
    result = process_single(sample_request_file, tmp_path / "output" / "scan.pdf.structured.json", InterpreterConfig(), MockProvider(response_json=output))
    assert result["status"] == "error"
    assert "processing muss dict sein" in result["error"]


def test_malformed_rows_container_returns_structured_error(sample_request_file, sample_llm_output, tmp_path):
    output = copy.deepcopy(sample_llm_output)
    output["content"]["rows"] = {}
    result = process_single(sample_request_file, tmp_path / "output" / "scan.pdf.structured.json", InterpreterConfig(), MockProvider(response_json=output))
    assert result["status"] == "error"
    assert "content.rows muss list sein" in result["error"]


def test_malformed_row_entry_returns_structured_error(sample_request_file, sample_llm_output, tmp_path):
    output = copy.deepcopy(sample_llm_output)
    output["content"]["rows"] = ["bad-row"]
    result = process_single(sample_request_file, tmp_path / "output" / "scan.pdf.structured.json", InterpreterConfig(), MockProvider(response_json=output))
    assert result["status"] == "error"
    assert "content.rows[0]" in result["error"]
