from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.pipeline import OrchestratorCancelled, OrchestratorEngine
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import create_source, error_case_root, load_single_record, make_engine, make_ui_state, orchestrator_logs_root

from cases.pipeline_control_support import assert_no_route_artifacts


def test_run_can_be_cancelled_before_processing_starts(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = OrchestratorEngine(
        orchestrator_root=tmp_path / "orchestrator",
        modules=FakeModules({}),
        cancel_requested=lambda: True,
    )

    with pytest.raises(OrchestratorCancelled):
        engine.run(ui_state)


def test_run_cancellation_freezes_active_document_as_error_bundle(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    cancel_requested = False
    modules = FakeModules({})
    original_interpret = modules.interpret_document

    def interpret_then_cancel(request_path: Path, output_path: Path, **kwargs):
        nonlocal cancel_requested
        result = original_interpret(request_path, output_path, **kwargs)
        cancel_requested = True
        return result

    modules.interpret_document = interpret_then_cancel
    engine = OrchestratorEngine(
        orchestrator_root=tmp_path / "orchestrator",
        modules=modules,
        cancel_requested=lambda: cancel_requested,
    )

    with pytest.raises(OrchestratorCancelled):
        engine.run(ui_state)

    record = load_single_record(tmp_path)
    assert record.final_disposition == "error"
    assert record.current_location == "error_bundle"
    assert (error_case_root(ui_state, "Interpreter") / "originals" / "doc.pdf").exists()
    assert (error_case_root(ui_state, "Interpreter") / "raw_extracts" / "doc.pdf.raw.json").exists()
    assert (error_case_root(ui_state, "Interpreter") / "requests" / "doc.pdf" / "interpreter.request.json").exists()
    assert list((error_case_root(ui_state, "Interpreter") / "structured").glob("*.structured.json"))
    assert_no_route_artifacts(ui_state)


def test_run_fails_fast_on_blocking_healthcheck(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    engine = make_engine(tmp_path, _blocking_healthcheck_scenario())

    with pytest.raises(RuntimeError, match="Healthcheck failed"):
        engine.run(ui_state)

    assert source.exists()
    assert engine._modules.healthcheck_calls == [
        (
            ("optimizer", "interpreter", "validator", "normalizer", "corpus_builder"),
            "pipeline_run",
            {"optimizer": ("pdf-pymupdf", "renderer-pdf")},
            str(Path(ui_state.corpus_output_folder) / "corpus.db"),
        )
    ]
    artifacts = list((orchestrator_logs_root(tmp_path) / "runs").rglob("healthcheck.failure.json"))
    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert payload["scope"] == "pipeline_run"
    assert payload["results"][0]["key"] == "interpreter"
    assert payload["results"][0]["dependencies"][0]["detail"] == "OPENAI_API_KEY is not set"
    assert engine.snapshot.stage_statuses["Interpreter"].status == "Error"
    assert "OPENAI_API_KEY is not set" in engine.snapshot.stage_statuses["Interpreter"].detail


def _blocking_healthcheck_scenario() -> dict:
    return {
        "__healthcheck__": {
            "pipeline_run": [
                {
                    "key": "interpreter",
                    "display_name": "Interpreter",
                    "healthy": False,
                    "message": "Provider not ready",
                    "dependencies": [
                        {
                            "name": "llm_provider",
                            "required": True,
                            "healthy": False,
                            "detail": "OPENAI_API_KEY is not set",
                        }
                    ],
                }
            ]
        }
    }
