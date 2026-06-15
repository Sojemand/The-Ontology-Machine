from __future__ import annotations

from pathlib import Path

from tests.pipeline_harness import create_source, error_case_root, load_single_record, make_engine, make_ui_state, route_root, run_log_files, runtime_files
from .pipeline_route_assertions import _assert_no_route_artifacts

def test_validator_fail_after_three_attempts_goes_to_error_bundle(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    scenarios = {"doc.pdf": {"validate": [{"status": "FAIL"}, {"status": "FAIL"}, {"status": "FAIL"}]}}
    summary = make_engine(tmp_path, scenarios).run(ui_state)
    record = load_single_record(tmp_path)

    assert summary.errors == 1
    assert summary.retries == 2
    assert record.failed_attempts == 3
    assert record.final_disposition == "error"
    assert record.current_location == "error_bundle"
    assert "Error Cases\\Validator\\Documents\\originals\\doc.pdf" in record.source_path
    assert (error_case_root(ui_state, "Validator") / "logs" / "doc.pdf.error_manifest.json").exists()
    assert (error_case_root(ui_state, "Validator") / "raw_extracts" / "doc.pdf.raw.json").exists()
    assert Path(record.artifacts.structured_path).exists()
    assert Path(record.artifacts.validation_report_path).exists()
    _assert_no_route_artifacts(ui_state)
    assert runtime_files(tmp_path) == []

def test_validator_warn_continues_without_retry_and_marks_review(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    summary = make_engine(
        tmp_path,
        {"doc.pdf": {"validate": {"status": "WARN", "detail": "WARN (issues=1, fail=0, warn=1)"}}},
    ).run(ui_state)
    record = load_single_record(tmp_path)

    assert summary.errors == 0
    assert summary.success == 1
    assert summary.needs_review == 1
    assert summary.retries == 0
    assert record.failed_attempts == 0
    assert record.validator_needs_review is True
    assert record.validator_review_reason == "WARN (issues=1, fail=0, warn=1)"
    assert record.review_reason == "WARN (issues=1, fail=0, warn=1)"
    assert record.final_disposition == "needs_review"
    assert record.current_location == "originals_archive"
    log_text = "\n".join(path.read_text(encoding="utf-8") for path in run_log_files(tmp_path))
    assert "Validator -> WARN" not in log_text
    assert "[VALIDATOR-REVIEW] doc.pdf: WARN (issues=1, fail=0, warn=1)" in log_text
    assert runtime_files(tmp_path) == []

def test_validator_missing_report_fails_closed(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    report_path = route_root(ui_state) / "logs" / "missing.report.json"
    engine = make_engine(tmp_path, {"doc.pdf": {"validate": {"status": "PASS", "report_path": str(report_path), "create_report": False}}})

    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert "Validator report is missing" in load_single_record(tmp_path).last_error
    assert engine._modules.loaded_paths == []

def test_validator_external_report_is_rejected(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    external_report = tmp_path / "external" / "doc.vision_validation_report.json"
    engine = make_engine(tmp_path, {"doc.pdf": {"validate": {"status": "PASS", "report_path": str(external_report)}}})

    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert "outside the pipeline" in load_single_record(tmp_path).last_error
    assert external_report.exists()
    assert engine._modules.loaded_paths == []
