from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import policy
from tests.pipeline_harness import artifact_root, create_source, error_case_root, load_single_record, make_engine, make_ui_state, route_root, runtime_files

def test_interpreter_error_moves_bundle_and_retries_to_success(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    scenarios = {"doc.pdf": {"interpret": [{"status": "error", "error": "llm timeout"}, {"status": "ok"}]}}
    summary = make_engine(tmp_path, scenarios).run(ui_state)

    file_route = route_root(ui_state)
    assert summary.success == 1
    assert summary.retries == 1
    assert not (error_case_root(ui_state, "Interpreter") / "raw_extracts" / "doc.pdf.raw.json").exists()
    assert (file_route / "originals" / "doc.pdf").exists()
    assert not source.exists()
    assert list((file_route / "raw_extracts").glob("*.raw.json"))
    assert not (artifact_root(ui_state) / "structured").exists()
    assert runtime_files(tmp_path) == []

def test_multipage_interpreter_retry_reprocesses_only_failed_page(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = make_engine(
        tmp_path,
        {
            "doc.pdf": {
                "extract": {"status": "ok", "page_count": 3},
                "interpret": [
                    {"status": "ok"},
                    {"status": "error", "error": "page 2 timeout"},
                    {"status": "ok"},
                    {"status": "ok"},
                ],
            }
        },
    )

    summary = engine.run(ui_state)

    assert summary.success == 1
    assert summary.retries == 1
    assert len(engine._modules.extract_calls) == 1
    assert len(engine._modules.interpret_calls) == 4
    assert ".p001.of003" in engine._modules.interpret_calls[0]
    assert ".p002.of003" in engine._modules.interpret_calls[1]
    assert ".p002.of003" in engine._modules.interpret_calls[2]
    assert ".p003.of003" in engine._modules.interpret_calls[3]
    request_status = engine.snapshot.stage_statuses["Request Enrichment"]
    interpreter_status = engine.snapshot.stage_statuses["Interpreter"]
    assert request_status.status == "Done"
    assert request_status.progress_current == 3
    assert request_status.progress_total == 3
    assert interpreter_status.status == "Done"
    assert interpreter_status.progress_current == 3
    assert interpreter_status.progress_total == 3
    assert len(engine._modules.loaded_paths) == 3
    assert not list((error_case_root(ui_state, "Interpreter") / "originals").rglob("*.*"))

def test_multipage_exhausted_page_becomes_page_error_without_blocking_other_pages(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = make_engine(
        tmp_path,
        {
            "doc.pdf": {
                "extract": {"status": "ok", "page_count": 2},
                "interpret": [
                    {"status": "ok"},
                    {"status": "error", "error": "page 2 timeout"},
                    {"status": "error", "error": "page 2 timeout"},
                    {"status": "error", "error": "page 2 timeout"},
                ],
            }
        },
    )

    summary = engine.run(ui_state)
    record = load_single_record(tmp_path)

    assert summary.success == 1
    assert summary.needs_review == 1
    assert summary.errors == 0
    assert summary.retries == 2
    assert len(engine._modules.loaded_paths) == 1
    assert record.final_disposition == "needs_review"
    assert record.current_location == "originals_archive"
    assert "Page 2/2 failed" in record.review_reason
    page_manifests = list((error_case_root(ui_state, "Interpreter") / "logs").rglob("*.p002.of002.error_manifest.json"))
    assert len(page_manifests) == 1
    assert not list((error_case_root(ui_state, "Interpreter") / "originals").rglob("*.*"))

def test_multiple_page_errors_keep_distinct_bundle_diagnostics(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = make_engine(
        tmp_path,
        {
            "doc.pdf": {
                "extract": {"status": "ok", "page_count": 3},
                "interpret": [
                    {"status": "ok"},
                    {"status": "error", "error": "page 2 timeout", "debug_payload": {"page": 2, "attempt": 1}},
                    {"status": "error", "error": "page 2 timeout", "debug_payload": {"page": 2, "attempt": 2}},
                    {"status": "error", "error": "page 2 timeout", "debug_payload": {"page": 2, "attempt": 3}},
                    {"status": "error", "error": "page 3 timeout", "debug_payload": {"page": 3, "attempt": 1}},
                    {"status": "error", "error": "page 3 timeout", "debug_payload": {"page": 3, "attempt": 2}},
                    {"status": "error", "error": "page 3 timeout", "debug_payload": {"page": 3, "attempt": 3}},
                ],
            }
        },
    )

    summary = engine.run(ui_state)
    error_root = error_case_root(ui_state, "Interpreter")

    assert summary.success == 1
    assert summary.needs_review == 1
    assert summary.errors == 0
    assert len(engine._modules.loaded_paths) == 1
    assert (error_root / "raw_extracts" / "doc.pdf.p002.of003.raw.json").exists()
    assert (error_root / "raw_extracts" / "doc.pdf.p003.of003.raw.json").exists()
    assert (error_root / "requests" / "doc.pdf.p002.of003" / policy.request_file_name()).exists()
    assert (error_root / "requests" / "doc.pdf.p003.of003" / policy.request_file_name()).exists()
    assert (error_root / "debug" / "p002.of003" / "doc.pdf.debug.json").exists()
    assert (error_root / "debug" / "p003.of003" / "doc.pdf.debug.json").exists()
    assert len(list((error_root / "logs").rglob("*.p002.of003.error_manifest.json"))) == 1
    assert len(list((error_root / "logs").rglob("*.p003.of003.error_manifest.json"))) == 1
    assert not list((error_root / "originals").rglob("*.*"))
