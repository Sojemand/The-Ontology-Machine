from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from llm_interpreter.interpreter import process_single, workflow
from llm_interpreter.models import InterpreterConfig


class MockProvider:
    provider_name = "mock"

    def __init__(self, response_text: str, *, model: str = "gpt-5.4"):
        self.response_text = response_text
        self._last_usage = {"input_tokens": 12, "output_tokens": 8}
        self._last_model = model

    def generate(self, **_kwargs):
        return self.response_text


def test_process_single_reports_parse_response_stage(tmp_path: Path, sample_request: dict) -> None:
    result = process_single(sample_request, tmp_path / "parse-error.json", InterpreterConfig(max_retries=0), MockProvider("not-json"))

    assert result["status"] == "error"
    assert result["error"].startswith("parse_response:")


def test_run_single_reports_write_output_stage(tmp_path: Path, sample_request: dict, sample_llm_output: dict) -> None:
    provider = MockProvider(json.dumps(sample_llm_output))

    result = workflow.run_single(
        sample_request,
        tmp_path / "write-error.json",
        InterpreterConfig(max_retries=0),
        provider,
        create_provider_fn=lambda *_args, **_kwargs: provider,
        write_json_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("locked")),
        backoff_fn=lambda _provider, _messages, _config, _label: (json.dumps(sample_llm_output), None),
    )

    assert result["status"] == "error"
    assert result["error"].startswith("write_output:")


def test_process_single_writes_debug_bundle_when_enabled(tmp_path: Path, sample_request: dict, sample_llm_output: dict) -> None:
    debug_dir = tmp_path / "debug"
    config = InterpreterConfig(max_retries=0, debug_bundle_dir=debug_dir)

    result = process_single(sample_request, tmp_path / "debug-output.json", config, MockProvider(json.dumps(sample_llm_output)))

    bundles = list(debug_dir.glob("*.debug.json"))
    payload = json.loads(bundles[0].read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert len(bundles) == 1
    assert payload["label"] == "scan.pdf"
    assert "prompt_view" not in payload
    assert "raw_provider_text" in payload
    assert "parsed_payload" in payload
    assert "persisted_payload" in payload
    assert "failed_stage" not in payload


def test_process_single_records_failed_stage_in_debug_bundle(tmp_path: Path, sample_request: dict) -> None:
    debug_dir = tmp_path / "debug"
    config = InterpreterConfig(max_retries=0, debug_bundle_dir=debug_dir)

    result = process_single(sample_request, tmp_path / "parse-output.json", config, MockProvider("not-json"))

    payload = json.loads(next(debug_dir.glob("*.debug.json")).read_text(encoding="utf-8"))
    assert result["status"] == "error"
    assert payload["failed_stage"] == "parse_response"
    assert payload["error"].startswith("JSON-Parse-Fehler")


def test_enrich_output_stage_prefix_is_visible(tmp_path: Path, sample_request: dict, sample_llm_output: dict) -> None:
    with patch("llm_interpreter.interpreter.workflow.domain.enrich_output", side_effect=RuntimeError("kaputt")):
        result = process_single(
            sample_request,
            tmp_path / "enrich-error.json",
            InterpreterConfig(max_retries=0),
            MockProvider(json.dumps(sample_llm_output)),
        )

    assert result["status"] == "error"
    assert result["error"].startswith("enrich_output:")
