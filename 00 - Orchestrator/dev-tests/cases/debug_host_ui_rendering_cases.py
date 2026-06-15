from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.debug_host.types import DebugPlan, DebugResult, DebugStep
from orchestrator.ui import debug_rendering

from cases.debug_host_ui_rendering_support import (
    assert_corpus_builder_single_controls,
    assert_normalizer_batch_controls,
    assert_optimizer_scan_controls,
    assert_validator_batch_controls,
    debug_plan_for,
    session,
    single_step_plan,
)
from support.debug_host_ui_support_impl import TextBox, make_app


def test_debug_rendering_applies_plan_status_and_button_states(monkeypatch, tmp_path: Path) -> None:
    app = make_app(tmp_path)
    selected_source = tmp_path / "incoming" / "invoice.pdf"
    selected_source.parent.mkdir(parents=True, exist_ok=True)
    selected_source.write_text("pdf", encoding="utf-8")
    app._debug_module_var.set("interpreter")
    app._debug_mode_var.set("single")
    app._debug_source_entry.insert(0, str(selected_source))
    app._debug_log_box = TextBox()
    session_root = tmp_path / "session"
    session_root.mkdir()
    run_log = session_root / "run.log"
    run_log.write_text("started\n", encoding="utf-8")
    app._debug_session = SimpleNamespace(
        active_step=None,
        session_root=session_root,
        output_root=session_root / "outputs",
        run_log_path=run_log,
        snapshot=None,
        result=DebugResult(
            status="ok",
            summary="completed",
            outputs={
                "interpreter_request": ["outputs/requests/docs/invoice.pdf/interpreter.request.json"],
                "structured_output": ["outputs/scan.pdf.structured.json"],
            },
        ),
    )

    monkeypatch.setattr("orchestrator.ui.debug_rendering.plan_for", debug_plan_for)
    debug_rendering.apply_view(app)

    assert "Request Enrichment" in app._debug_plan_label.value
    assert app._debug_status_label.value.endswith("OK")
    assert app._debug_artifact_summary_label.value == "1 artifacts loaded"
    assert app._debug_console_cards["advanced"].visible is False
    assert "Source Path" in app._debug_target_hint_label.value
    assert app._debug_replay_status_label.value == "No replay loaded."
    assert app._debug_help_btn.config["state"] == "normal"
    assert app._debug_module_menu.config["values"] == [
        "Optimizer",
        "Interpreter",
        "Validator",
        "Normalizer",
        "Corpus Builder",
    ]
    assert app._debug_mode_menu.config["state"] == "normal"
    assert app._debug_start_btn.config["state"] == "normal"
    assert app._debug_control_rows["source_path"].visible is True
    assert app._debug_control_rows["input_path"].visible is False
    assert all(app._debug_control_rows[key].visible is False for key in ("format", "doc_type", "worker_count", "hash_tools"))

    assert_validator_batch_controls(app, tmp_path)
    assert_optimizer_scan_controls(app)
    assert_normalizer_batch_controls(app, tmp_path)
    assert_corpus_builder_single_controls(app, tmp_path)


def test_debug_rendering_keeps_session_files_visible_beside_validator_outputs(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._debug_module_var.set("validator")
    app._debug_mode_var.set("single")
    structured_path = tmp_path / "structured" / "invoice.structured.json"
    structured_path.parent.mkdir(parents=True, exist_ok=True)
    structured_path.write_text("{}", encoding="utf-8")
    app._debug_input_entry.insert(0, str(structured_path))
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    report_path = output_root / "validation_reports" / "invoice.files_validation_report.json"
    config_path = output_root / "config_snapshot.json"
    index_path = output_root / "report_index.json"
    for path, payload in (
        (session_root / "request.json", "{}"),
        (session_root / "response.json", "{}"),
        (session_root / "snapshot.json", "{}"),
        (session_root / "result.json", "{}"),
        (session_root / "run.log", "started\n"),
        (
            report_path,
            '{"result":"PASS","file_name":"invoice.pdf","summary":{"total_issues":0,"fail_count":0,"warn_count":0}}',
        ),
        (config_path, "{}"),
        (index_path, "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    app._debug_session = session(session_root, output_root, DebugResult(status="ok", summary="done", outputs={
        "validation_reports": [str(report_path.relative_to(session_root).as_posix())],
        "config_snapshot": [str(config_path.relative_to(session_root).as_posix())],
        "report_index": [str(index_path.relative_to(session_root).as_posix())],
    }))
    monkeypatch.setattr("orchestrator.ui.debug_rendering.plan_for", single_step_plan)

    debug_rendering.apply_view(app)

    names = {entry.path.name for entry in app._debug_artifact_entries}
    assert {
        "request.json",
        "response.json",
        "snapshot.json",
        "result.json",
        "run.log",
        "invoice.files_validation_report.json",
        "config_snapshot.json",
        "report_index.json",
    }.issubset(names)
    assert app._debug_artifact_summary_label.value == "8 artifacts: 1 PASS  0 WARN  0 FAIL"


def test_debug_rendering_includes_undeclared_output_tree_files(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._input_entry.insert(0, str(tmp_path / "input"))
    app._debug_module_var.set("optimizer")
    app._debug_mode_var.set("single")
    app._debug_source_entry.insert(0, "incoming/sample.pdf")
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    raw_path = output_root / "raw_extracts" / "incoming" / "sample.pdf.raw.json"
    page_path = output_root / "page_images" / "incoming" / "sample.pdf.hash" / "page_001.jpg"
    request_path = output_root / "requests" / "incoming" / "sample.pdf" / "interpreter.request.json"
    for path, payload in (
        (session_root / "request.json", "{}"),
        (session_root / "response.json", "{}"),
        (session_root / "snapshot.json", "{}"),
        (session_root / "result.json", "{}"),
        (session_root / "run.log", "started\n"),
        (raw_path, '{"schema_version":"optimizer_raw_v1"}'),
        (page_path, "jpg"),
        (request_path, '{"request":"ok"}'),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    app._debug_session = session(session_root, output_root, DebugResult(status="ok", summary="done", outputs={
        "raw_extracts": [str(raw_path.relative_to(session_root).as_posix())],
        "page_images": [str(page_path.relative_to(session_root).as_posix())],
    }))
    monkeypatch.setattr("orchestrator.ui.debug_rendering.plan_for", single_step_plan)

    debug_rendering.apply_view(app)

    names = {entry.path.name for entry in app._debug_artifact_entries}
    assert {"sample.pdf.raw.json", "page_001.jpg", "interpreter.request.json"}.issubset(names)
