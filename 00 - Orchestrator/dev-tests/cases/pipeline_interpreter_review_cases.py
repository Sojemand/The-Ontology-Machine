from __future__ import annotations

from pathlib import Path

import pytest

from tests.pipeline_harness import create_source, error_case_root, load_single_record, make_engine, make_ui_state, route_root, runtime_files
from .pipeline_route_assertions import _assert_no_route_artifacts

def test_interpreter_review_passes_to_downstream_and_marks_review(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    summary = make_engine(tmp_path, {"doc.pdf": {"interpret": {"status": "ok_review", "needs_review": True, "review_reason": "check me"}}}).run(ui_state)

    assert summary.errors == 0
    assert summary.success == 1
    assert summary.needs_review == 1
    assert summary.retries == 0
    record = load_single_record(tmp_path)
    assert record.final_disposition == "needs_review"
    assert record.current_location == "originals_archive"
    assert record.interpreter_needs_review is True
    assert record.interpreter_review_reason == "check me"
    assert record.review_reason == "check me"
    assert Path(record.artifacts.structured_path).exists()
    assert not (error_case_root(ui_state, "Interpreter") / "logs" / "doc.pdf.error_manifest.json").exists()
    assert Path(record.artifacts.normalized_path).exists()
    assert Path(record.artifacts.validation_report_path).exists()
    assert runtime_files(tmp_path) == []

def test_long_docx_name_succeeds_without_runtime_path_budget_failures(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    file_name = (
        "201611136 V - L - Reinhard Feinmechanik Dietzenbach - "
        "Anlieferung von 20 Stück Rohlingen Ø60 x 440-290mm lang .docx"
    )
    create_source(ui_state, file_name)

    summary = make_engine(tmp_path, {file_name: {}}).run(ui_state)

    assert summary.success == 1
    assert summary.errors == 0
    assert list((route_root(ui_state) / "structured").glob("*.structured.json"))
    assert list((route_root(ui_state) / "validation").glob("*.files_validation_report.json"))
    assert runtime_files(tmp_path) == []

def test_malformed_processing_payload_uses_root_review_fields_without_crashing(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    scenarios = {
        "doc.pdf": {
            "interpret": {
                "status": "ok_review",
                "structured_payload": {
                    "processing": "broken",
                    "needs_review": True,
                    "review_reason": "root review",
                },
            }
        }
    }
    summary = make_engine(tmp_path, scenarios).run(ui_state)

    assert summary.errors == 0
    assert summary.success == 1
    assert summary.needs_review == 1
    record = load_single_record(tmp_path)
    assert record.final_disposition == "needs_review"
    assert record.interpreter_review_reason == "root review"
    assert record.review_reason == "root review"

@pytest.mark.parametrize(
    ("interpret_outcome", "error_snippet"),
    [
        ({"status": "ok", "structured_text": "{not json]"}, "invalid structured JSON"),
        ({"status": "ok", "create_structured": False}, "Structured output could not be imported"),
    ],
    ids=["malformed", "missing"],
)
def test_bad_interpreter_output_fails_cleanly_without_partial_success(
    tmp_path: Path,
    interpret_outcome: dict[str, object],
    error_snippet: str,
) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    summary = make_engine(tmp_path, {"doc.pdf": {"interpret": interpret_outcome}}).run(ui_state)
    record = load_single_record(tmp_path)

    assert summary.success == 0
    assert summary.errors == 1
    assert summary.retries == 2
    assert record.status == "error"
    assert record.final_disposition == "error"
    assert record.last_stage == "Interpreter"
    assert record.current_location == "error_bundle"
    assert error_snippet in record.last_error
    assert not (Path(ui_state.corpus_output_folder) / "corpus.db").exists()
    _assert_no_route_artifacts(ui_state)
    assert runtime_files(tmp_path) == []
