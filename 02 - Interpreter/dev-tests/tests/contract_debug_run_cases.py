from __future__ import annotations

import json

from llm_interpreter.models import InterpreterConfig
from llm_interpreter.orchestrator_contract import _debug_run


def test_debug_run_writes_session_artifacts_and_normalizes_review(monkeypatch, sample_request_file, tmp_path) -> None:
    session_root = tmp_path / "session"
    captured = {}

    def _fake_process_single(request_input, output_path, _config):
        captured["request_input"] = request_input
        captured["output_path"] = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        return {
            "status": "ok_review",
            "output_path": str(output_path),
            "needs_review": True,
            "review_reason": "review required",
        }

    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.process_single", _fake_process_single)

    result = _debug_run(
        {
            "session_root": str(session_root),
            "request_path": str(sample_request_file),
            "output_root": str(session_root / "outputs"),
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
        }
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))
    persisted = json.loads((session_root / "result.json").read_text(encoding="utf-8"))

    assert result["status"] == "ok"
    assert result["outputs"]["structured_output"] == ["outputs/scan.pdf.structured.json"]
    assert result["metrics"]["needs_review"] is True
    assert "Review erforderlich" in result["summary"]
    assert captured["request_input"].request_path == sample_request_file.resolve(strict=False)
    assert captured["output_path"] == session_root / "outputs" / "scan.pdf.structured.json"
    assert snapshot["status"] == "ok"
    assert persisted["metrics"]["review_reason"] == "review required"


def test_debug_run_writes_error_result_for_invalid_request(tmp_path, monkeypatch) -> None:
    session_root = tmp_path / "session"
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())

    result = _debug_run(
        {
            "session_root": str(session_root),
            "request_path": str(tmp_path / "missing.request.json"),
            "output_root": str(session_root / "outputs"),
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
        }
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))
    assert result["status"] == "error"
    assert "Request nicht gefunden" in result["error"]
    assert snapshot["status"] == "error"


def test_debug_run_prefers_cancelled_terminal_state(monkeypatch, sample_request_file, tmp_path) -> None:
    session_root = tmp_path / "session"

    def _fake_process_single(_request_input, output_path, _config):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        (session_root / "cancel.request").write_text("", encoding="utf-8")
        return {
            "status": "ok",
            "output_path": str(output_path),
            "needs_review": False,
            "review_reason": "",
        }

    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.process_single", _fake_process_single)

    result = _debug_run(
        {
            "session_root": str(session_root),
            "request_path": str(sample_request_file),
            "output_root": str(session_root / "outputs"),
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
        }
    )

    assert result["status"] == "cancelled"
    assert json.loads((session_root / "result.json").read_text(encoding="utf-8"))["status"] == "cancelled"


def test_debug_run_batch_writes_structured_outputs_and_metrics(monkeypatch, tmp_path) -> None:
    session_root = tmp_path / "session"
    request_root = tmp_path / "requests"
    request_root.mkdir()
    captured = {}

    def _fake_process_batch(input_root, output_root, _config, num_workers=1, on_progress=None, should_cancel=None):
        captured["input_root"] = input_root
        captured["output_root"] = output_root
        captured["num_workers"] = num_workers
        first_output = output_root / "batch" / "a.structured.json"
        second_output = output_root / "batch" / "b.structured.json"
        first_output.parent.mkdir(parents=True, exist_ok=True)
        first_output.write_text("{}", encoding="utf-8")
        second_output.write_text("{}", encoding="utf-8")
        if on_progress is not None:
            on_progress({"status": "ok", "file": "a.request.json", "needs_review": False}, 1, 2)
            on_progress({"status": "ok_review", "file": "b.request.json", "needs_review": True}, 2, 2)
        return {
            "ok": 2,
            "error": 0,
            "total": 2,
            "total_cost_usd": 0.5,
            "results": [
                {"status": "ok", "file": "a.request.json", "output_path": str(first_output), "needs_review": False},
                {"status": "ok_review", "file": "b.request.json", "output_path": str(second_output), "needs_review": True},
            ],
        }

    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.process_batch", _fake_process_batch)

    result = _debug_run(
        {
            "session_root": str(session_root),
            "mode": "batch",
            "input_root": str(request_root),
            "output_root": str(session_root / "outputs" / "structured_output"),
            "num_workers": 1,
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
        }
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))

    assert result["status"] == "ok"
    assert result["summary"] == "Batch abgeschlossen (Review erforderlich)"
    assert result["outputs"]["structured_output"] == [
        "outputs/structured_output/batch/a.structured.json",
        "outputs/structured_output/batch/b.structured.json",
    ]
    assert result["metrics"] == {"ok": 2, "error": 0, "total": 2, "needs_review": 1, "total_cost_usd": 0.5}
    assert captured["input_root"] == request_root
    assert captured["output_root"] == session_root / "outputs" / "structured_output"
    assert captured["num_workers"] == 1
    assert snapshot["processed"] == 2
    assert snapshot["total"] == 2


def test_debug_run_batch_prefers_cancelled_state_during_progress(monkeypatch, tmp_path) -> None:
    session_root = tmp_path / "session"
    request_root = tmp_path / "requests"
    request_root.mkdir()

    def _fake_process_batch(_input_root, _output_root, _config, num_workers=1, on_progress=None, should_cancel=None):
        assert should_cancel is not None
        if on_progress is not None:
            on_progress({"status": "ok", "file": "a.request.json", "needs_review": False}, 1, 2)
        (session_root / "cancel.request").write_text("", encoding="utf-8")
        assert should_cancel() is True
        return {
            "ok": 1,
            "error": 0,
            "total": 2,
            "total_cost_usd": None,
            "results": [{"status": "ok", "file": "a.request.json", "output_path": ""}],
        }

    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_dotenv", lambda: None)
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.load_config", lambda: InterpreterConfig())
    monkeypatch.setattr("llm_interpreter.orchestrator_contract.process_batch", _fake_process_batch)

    result = _debug_run(
        {
            "session_root": str(session_root),
            "mode": "batch",
            "input_root": str(request_root),
            "output_root": str(session_root / "outputs" / "structured_output"),
            "num_workers": 1,
            "runtime_settings": {"model": "gpt-5.4", "max_output_tokens": 8000},
        }
    )

    assert result["status"] == "cancelled"
    assert json.loads((session_root / "result.json").read_text(encoding="utf-8"))["status"] == "cancelled"
