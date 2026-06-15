from __future__ import annotations

from pathlib import Path

from orchestrator.state import load_pipeline_state
from tests.pipeline_harness import create_source, make_engine, make_ui_state, orchestrator_logs_root, pipeline_state_path, route_root


def test_reset_pipeline_logs_removes_hidden_pipeline_state_but_keeps_outputs(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    engine = make_engine(tmp_path, scenarios={})
    create_source(ui_state)

    first_summary = engine.run(ui_state)
    reset_summary = engine.reset_pipeline_logs(ui_state)
    state = load_pipeline_state(pipeline_state_path(tmp_path))

    assert first_summary.success == 1
    assert reset_summary.cleared_records == 1
    assert reset_summary.removed_pipeline_targets == ("state/pipeline",)
    assert not pipeline_state_path(tmp_path).exists()
    assert not orchestrator_logs_root(tmp_path).exists()
    assert (route_root(ui_state) / "originals" / "doc.pdf").exists()
    assert (Path(ui_state.corpus_output_folder) / "corpus.db").exists()
    assert state.documents == {}


def test_reset_pipeline_logs_allows_success_document_to_run_again(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    engine = make_engine(tmp_path, scenarios={})
    create_source(ui_state, content="same")

    first_summary = engine.run(ui_state)
    engine.reset_pipeline_logs(ui_state)
    create_source(ui_state, content="same")
    second_summary = engine.run(ui_state)
    state = load_pipeline_state(pipeline_state_path(tmp_path))

    assert first_summary.success == 1
    assert second_summary.success == 1
    assert len(state.documents) == 1
    assert next(iter(state.documents.values())).final_disposition == "success"
