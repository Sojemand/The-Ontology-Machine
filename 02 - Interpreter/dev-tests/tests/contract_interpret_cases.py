from __future__ import annotations

from llm_interpreter.models import InterpreterConfig
from llm_interpreter.orchestrator_contract import _interpret_document


def test_interpret_document_loads_request_path(monkeypatch, sample_request_file, tmp_path) -> None:
    captured = {}

    def _fake_process_single(request_input, output_path, _config):
        captured["request_input"] = request_input
        captured["output_path"] = output_path
        captured["config_model"] = _config.model
        captured["config_max_output_tokens"] = _config.max_output_tokens
        captured["config_thinking_effort"] = _config.thinking_effort
        return {"status": "ok", "output_path": str(output_path), "needs_review": False, "review_reason": ""}

    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.process_single", _fake_process_single)
    result = _interpret_document(
        {
            "request_path": str(sample_request_file),
            "structured_output_path": str(tmp_path / "output" / "doc.structured.json"),
            "runtime_settings": {"model": "gpt-4.1", "max_output_tokens": 4096},
        }
    )

    assert result["status"] == "ok"
    assert captured["output_path"] == tmp_path / "output" / "doc.structured.json"
    assert captured["request_input"].request_path == sample_request_file.resolve(strict=False)
    assert captured["request_input"].asset_roots[0] == sample_request_file.parent.resolve(strict=False)
    assert captured["config_model"] == "gpt-4.1"
    assert captured["config_max_output_tokens"] == 4096
    assert captured["config_thinking_effort"] == "no thinking"
