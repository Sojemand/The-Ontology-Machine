from __future__ import annotations

import copy
import json
from pathlib import Path

from llm_interpreter.interpreter import process_single
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.orchestrator_contract import _interpret_document


class MockProvider:
    provider_name = "mock"

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self._last_usage = {"input_tokens": 1, "output_tokens": 1}
        self._last_model = "gpt-5.4"

    def generate(self, **_kwargs):
        return self.response_text


def test_process_single_returns_debug_bundle_path_when_enabled(tmp_path: Path, sample_request: dict, sample_llm_output: dict) -> None:
    debug_dir = tmp_path / "debug"

    result = process_single(
        sample_request,
        tmp_path / "out.json",
        InterpreterConfig(max_retries=0, debug_bundle_dir=debug_dir),
        MockProvider(json.dumps(sample_llm_output)),
    )

    bundle_path = next(debug_dir.glob("*.debug.json"))
    assert result["status"] == "ok"
    assert result["debug_bundle_path"] == str(bundle_path)


def test_debug_bundle_name_is_capped_for_long_source_file_names(
    tmp_path: Path,
    sample_request: dict,
    sample_llm_output: dict,
) -> None:
    debug_dir = tmp_path / "debug"
    request = copy.deepcopy(sample_request)
    request["source"]["file_name"] = ("a" * 245) + ".pdf"

    result = process_single(
        request,
        tmp_path / "out.json",
        InterpreterConfig(max_retries=0, debug_bundle_dir=debug_dir),
        MockProvider(json.dumps(sample_llm_output)),
    )

    bundle_path = next(debug_dir.glob("*.debug.json"))
    assert result["status"] == "ok"
    assert len(bundle_path.name) <= 120
    assert bundle_path.name.endswith(".debug.json")


def test_interpret_document_applies_debug_bundle_dir_and_returns_bundle_path(
    monkeypatch,
    sample_request_file: Path,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    debug_dir = tmp_path / "runtime-debug"
    debug_bundle_path = debug_dir / "scan.debug.json"

    def fake_process_single(_request_input, output_path: Path, config) -> dict:
        captured["debug_bundle_dir"] = config.debug_bundle_dir
        return {
            "status": "ok",
            "output_path": str(output_path),
            "debug_bundle_path": str(debug_bundle_path),
            "needs_review": False,
            "review_reason": "",
        }

    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.process_single", fake_process_single)

    result = _interpret_document(
        {
            "request_path": str(sample_request_file),
            "structured_output_path": str(tmp_path / "out" / "scan.structured.json"),
            "debug_bundle_dir": str(debug_dir),
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
        }
    )

    assert result["status"] == "ok"
    assert result["debug_bundle_path"] == str(debug_bundle_path)
    assert captured["debug_bundle_dir"] == debug_dir
