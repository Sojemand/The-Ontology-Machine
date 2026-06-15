"""Tests for batch orchestration."""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from llm_interpreter.interpreter import process_batch
from llm_interpreter.interpreter.adapter import default_output_name
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.providers import ProviderError
from tests.support.provider_stubs import MockProvider


def _write_batch_inputs(sample_request: dict, input_dir: Path, tmp_path: Path, *, count: int = 2, shared_name: str | None = None) -> None:
    input_dir.mkdir(parents=True)
    page_root = tmp_path / ("page_assets_duplicates" if shared_name else "page_assets")
    for index in range(count):
        request = copy.deepcopy(sample_request)
        request["source"]["file_name"] = shared_name or f"doc_{index}.pdf"
        request["source"]["file_path"] = str(tmp_path / f"doc_{index}.pdf")
        doc_dir = page_root / f"doc_{index}"
        doc_dir.mkdir(parents=True)
        for page in request["page_assets"]:
            source = Path(page["path"])
            target = doc_dir / source.name
            target.write_bytes(source.read_bytes())
            page["path"] = str(target)
        prefix = "duplicate" if shared_name else "doc"
        (input_dir / f"{prefix}_{index}.request.json").write_text(json.dumps(request), encoding="utf-8")


def test_batch_runs_multiple_files(sample_request, sample_llm_output, tmp_path):
    input_dir = tmp_path / "requests"
    _write_batch_inputs(sample_request, input_dir, tmp_path)
    with patch("llm_interpreter.interpreter.create_provider", return_value=MockProvider(response_json=sample_llm_output)):
        result = process_batch(input_dir, tmp_path / "output", InterpreterConfig(), num_workers=1)
    assert result["ok"] == 2
    assert result["error"] == 0


def test_batch_filters_non_request_files(sample_request, sample_llm_output, tmp_path):
    input_dir = tmp_path / "requests"
    input_dir.mkdir(parents=True)
    (input_dir / "doc.request.json").write_text(json.dumps(sample_request), encoding="utf-8")
    (input_dir / "doc.structured.json").write_text(json.dumps(sample_llm_output), encoding="utf-8")
    with patch("llm_interpreter.interpreter.create_provider", return_value=MockProvider(response_json=sample_llm_output)):
        result = process_batch(input_dir, tmp_path / "output", InterpreterConfig(), num_workers=1)
    assert result["total"] == 1
    assert result["results"][0]["file"] == "doc.request.json"


def test_batch_collects_nested_request_files(sample_request, sample_llm_output, tmp_path):
    nested_root = tmp_path / "requests" / "nested"
    _write_batch_inputs(sample_request, nested_root, tmp_path)

    with patch("llm_interpreter.interpreter.create_provider", return_value=MockProvider(response_json=sample_llm_output)):
        result = process_batch(tmp_path / "requests", tmp_path / "output", InterpreterConfig(), num_workers=1)

    assert result["total"] == 2


def test_default_output_name_caps_long_generated_file_names() -> None:
    first = default_output_name({"source": {"file_name": ("a" * 245) + "-one.pdf"}})
    second = default_output_name({"source": {"file_name": ("a" * 245) + "-two.pdf"}})
    unsafe = default_output_name({"source": {"file_name": 'client:invoice?.pdf'}})

    assert len(first) <= 120
    assert len(second) <= 120
    assert first != second
    assert first.endswith(".structured.json")
    assert ":" not in unsafe
    assert "?" not in unsafe


@pytest.mark.parametrize("workers", [1, 2])
def test_write_errors_are_structured_for_sequential_and_parallel_batch(workers, sample_request, sample_llm_output, tmp_path):
    input_dir = tmp_path / "requests"
    _write_batch_inputs(sample_request, input_dir, tmp_path)
    with patch("llm_interpreter.interpreter.create_provider", side_effect=lambda *_a, **_k: MockProvider(response_json=sample_llm_output)), patch(
        "llm_interpreter.interpreter.atomic_json_write",
        side_effect=OSError("disk full"),
    ):
        result = process_batch(input_dir, tmp_path / "output", InterpreterConfig(), num_workers=workers)
    assert result["ok"] == 0
    assert result["error"] == 2
    assert [item["status"] for item in result["results"]] == ["error", "error"]


def test_parallel_provider_creation_errors_are_structured(sample_request, tmp_path):
    input_dir = tmp_path / "requests"
    _write_batch_inputs(sample_request, input_dir, tmp_path)
    with patch("llm_interpreter.interpreter.create_provider", side_effect=ProviderError("missing key")):
        result = process_batch(input_dir, tmp_path / "output", InterpreterConfig(), num_workers=2)
    assert result["ok"] == 0
    assert result["error"] == 2
    assert all("missing key" in (item["error"] or "") for item in result["results"])


def test_sequential_batch_cancel_marks_remaining_without_starting_new_work(sample_request, sample_llm_output, tmp_path):
    input_dir = tmp_path / "requests"
    _write_batch_inputs(sample_request, input_dir, tmp_path, count=3)
    started: list[str] = []
    cancelled = {"value": False}

    def _process_single(file_path, output_path, _config, _provider):
        started.append(file_path.name)
        cancelled["value"] = True
        return {"status": "ok", "file": file_path.name, "output_path": str(output_path), "error": None, "cost_estimate_usd": 0.0}

    with patch("llm_interpreter.interpreter.create_provider", return_value=MockProvider(response_json=sample_llm_output)), patch(
        "llm_interpreter.interpreter.process_single",
        side_effect=_process_single,
    ):
        result = process_batch(
            input_dir,
            tmp_path / "output",
            InterpreterConfig(),
            num_workers=1,
            should_cancel=lambda: cancelled["value"],
        )

    assert started == ["doc_0.request.json"]
    assert result["ok"] == 1
    assert result["error"] == 2
    assert [item["status"] for item in result["results"]] == ["ok", "cancelled", "cancelled"]


def test_parallel_results_preserve_input_order(sample_request, tmp_path):
    input_dir = tmp_path / "requests"
    _write_batch_inputs(sample_request, input_dir, tmp_path)
    ordered_names = [path.name for path in sorted(input_dir.glob("*.request.json"))]

    def _process_single(file_path, output_path, _config, _provider):
        if file_path.name == ordered_names[0]:
            time.sleep(0.05)
        return {"status": "ok", "file": file_path.name, "output_path": str(output_path), "error": None, "cost_estimate_usd": 0.125}

    with patch("llm_interpreter.interpreter.create_provider", return_value=object()), patch(
        "llm_interpreter.interpreter.process_single",
        side_effect=_process_single,
    ):
        result = process_batch(input_dir, tmp_path / "output", InterpreterConfig(), num_workers=2)
    assert [item["file"] for item in result["results"]] == ordered_names
    assert result["total_cost_usd"] == 0.25


def test_empty_batch_includes_total_cost_field(tmp_path):
    result = process_batch(tmp_path / "requests", tmp_path / "output", InterpreterConfig(), num_workers=1)
    assert result == {"ok": 0, "error": 0, "total": 0, "total_cost_usd": None, "results": []}


@pytest.mark.parametrize("workers", [1, 2])
def test_duplicate_output_names_fail_closed(workers, sample_request, sample_llm_output, tmp_path):
    input_dir = tmp_path / "requests"
    _write_batch_inputs(sample_request, input_dir, tmp_path, shared_name="shared.pdf")
    progress_events: list[tuple[str, int, int]] = []
    with patch("llm_interpreter.interpreter.process_single") as mock_process_single, patch(
        "llm_interpreter.interpreter.create_provider",
        return_value=MockProvider(response_json=sample_llm_output),
    ):
        result = process_batch(
            input_dir,
            tmp_path / "output",
            InterpreterConfig(),
            num_workers=workers,
            on_progress=lambda item, done, total: progress_events.append((item["file"], done, total)),
        )
    assert result["ok"] == 0
    assert result["error"] == 2
    assert mock_process_single.call_count == 0
    assert all("Ausgabekollision" in (item["error"] or "") for item in result["results"])
    assert progress_events == [("duplicate_0.request.json", 1, 2), ("duplicate_1.request.json", 2, 2)]
