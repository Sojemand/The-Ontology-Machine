from __future__ import annotations

import json

from llm_interpreter.models import InterpreterConfig
from .interpreter_validation_support import clone_request, process_request_object


def test_process_single_accepts_valid_projection_hint(sample_request, sample_llm_output, sample_projection_catalog, tmp_path):
    request = clone_request(sample_request)
    request["projection_catalog"] = sample_projection_catalog
    sample_llm_output["context"]["projection_hint"] = _hint("operations.default.v1", confidence=0.72)

    result = process_request_object(request, tmp_path / "output" / "scan.pdf.structured.json", response_json=sample_llm_output)

    assert result["status"] == "ok"


def test_process_single_accepts_projection_hint_confidence_as_numeric_string(sample_request, sample_llm_output, sample_projection_catalog, tmp_path):
    request = clone_request(sample_request)
    request["projection_catalog"] = sample_projection_catalog
    sample_llm_output["context"]["projection_hint"] = _hint("operations.default.v1", confidence="0,72")
    output_path = tmp_path / "output" / "scan.pdf.structured.json"

    result = process_request_object(request, output_path, config=InterpreterConfig(), response_json=sample_llm_output)

    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert persisted["context"]["projection_hint"]["confidence"] == 0.72


def test_process_single_defaults_missing_projection_hint_confidence_to_zero(sample_request, sample_llm_output, sample_projection_catalog, tmp_path):
    request = clone_request(sample_request)
    request["projection_catalog"] = sample_projection_catalog
    sample_llm_output["context"]["projection_hint"] = {
        "projection_id": "operations.default.v1",
        "reason": "Transport- und Logistiksignale im Dokument.",
        "matched_signals": ["lieferschein"],
    }
    output_path = tmp_path / "output" / "scan-missing-confidence.pdf.structured.json"

    result = process_request_object(request, output_path, response_json=sample_llm_output)
    persisted = json.loads(output_path.read_text(encoding="utf-8"))

    assert result["status"] == "ok"
    assert persisted["context"]["projection_hint"]["confidence"] == 0.0


def test_process_single_drops_unknown_projection_hint(sample_request, sample_llm_output, sample_projection_catalog, tmp_path):
    request = clone_request(sample_request)
    request["projection_catalog"] = sample_projection_catalog
    sample_llm_output["context"]["projection_hint"] = _hint("missing.profile", confidence=0.72, matched_signals=["lieferschein"])
    output_path = tmp_path / "output" / "scan-unknown-hint.pdf.structured.json"

    result = process_request_object(request, output_path, response_json=sample_llm_output)
    persisted = json.loads(output_path.read_text(encoding="utf-8"))

    assert result["status"] == "ok"
    assert "projection_hint" not in persisted["context"]


def test_process_single_prunes_empty_projection_hint(sample_request, sample_llm_output, sample_projection_catalog, tmp_path):
    request = clone_request(sample_request)
    request["projection_catalog"] = sample_projection_catalog
    sample_llm_output["context"]["projection_hint"] = {
        "projection_id": None,
        "confidence": 0.0,
        "reason": None,
        "matched_signals": [],
    }
    output_path = tmp_path / "output" / "scan.pdf.structured.json"

    result = process_request_object(request, output_path, response_json=sample_llm_output)

    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert "projection_hint" not in persisted["context"]


def test_process_single_prunes_empty_projection_hint_object(sample_request, sample_llm_output, sample_projection_catalog, tmp_path):
    request = clone_request(sample_request)
    request["projection_catalog"] = sample_projection_catalog
    sample_llm_output["context"]["projection_hint"] = {}
    output_path = tmp_path / "output" / "scan-empty.pdf.structured.json"

    result = process_request_object(request, output_path, response_json=sample_llm_output)

    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["status"] == "ok"
    assert "projection_hint" not in persisted["context"]


def test_process_single_drops_non_object_projection_hint(sample_request, sample_llm_output, sample_projection_catalog, tmp_path):
    request = clone_request(sample_request)
    request["projection_catalog"] = sample_projection_catalog
    sample_llm_output["context"]["projection_hint"] = "operations.default.v1"
    output_path = tmp_path / "output" / "scan-string-hint.pdf.structured.json"

    result = process_request_object(request, output_path, response_json=sample_llm_output)
    persisted = json.loads(output_path.read_text(encoding="utf-8"))

    assert result["status"] == "ok"
    assert "projection_hint" not in persisted["context"]


def _hint(projection_id: str, *, confidence, matched_signals: list[str] | None = None) -> dict:
    return {
        "projection_id": projection_id,
        "confidence": confidence,
        "reason": "Transport- und Logistiksignale im Dokument.",
        "matched_signals": matched_signals or ["lieferschein", "transportauftrag"],
    }
