from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import OrchestratorEngine
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import create_source, load_single_record, make_ui_state


def test_main_run_triggers_embeddings_after_each_successful_corpus_load(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, "doc-a.pdf", content="doc-a")
    create_source(ui_state, "doc-b.pdf", content="doc-b")
    modules = FakeModules(
        {"__embeddings__": {"embed": [{"status": "completed", "count": 1, "reason": "1 embeddings generated."}, {"status": "completed", "count": 1, "reason": "1 embeddings generated."}]}}
    )
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)

    summary = engine.run(ui_state)

    assert summary.success == 2
    assert modules.embedding_calls == [str(Path(ui_state.corpus_output_folder) / "corpus.db")] * 2
    assert modules.embedding_force_flags == [False, False]
    assert engine.snapshot.stage_statuses["Embeddings"].status == "Done"
    assert engine.snapshot.stage_statuses["Embeddings"].detail == "1 embeddings generated."


def test_main_run_keeps_document_success_when_embeddings_are_disabled(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    modules = FakeModules({"__embeddings__": {"embed": {"status": "disabled", "reason": "Embeddings key missing"}}})
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)

    summary = engine.run(ui_state)

    assert summary.success == 1
    assert load_single_record(tmp_path).final_disposition == "success"
    assert engine.snapshot.stage_statuses["Embeddings"].status == "Warning"
    assert engine.snapshot.stage_statuses["Embeddings"].detail == "Embeddings key missing"


def test_main_run_routes_document_to_error_when_embeddings_fail(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    modules = FakeModules({"__embeddings__": {"embed": {"status": "error", "reason": "provider offline"}}})
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules, max_failed_attempts=1)

    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert modules.embedding_calls == [str(Path(ui_state.corpus_output_folder) / "corpus.db")]
    assert load_single_record(tmp_path).final_disposition == "error"
    assert load_single_record(tmp_path).last_stage == "Embeddings"
    assert engine.snapshot.stage_statuses["Embeddings"].status == "Error"
    assert engine.snapshot.stage_statuses["Embeddings"].detail == "provider offline"


def test_manual_embeddings_run_can_still_backfill_existing_corpus(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, "doc-a.pdf", content="doc-a")
    create_source(ui_state, "doc-b.pdf", content="doc-b")
    modules = FakeModules(
        {
            "__embeddings__": {
                "embed": [
                    {"status": "completed", "count": 1, "reason": "1 embeddings generated."},
                    {"status": "completed", "count": 1, "reason": "1 embeddings generated."},
                    {"status": "completed", "count": 1, "reason": "1 embeddings generated."},
                ]
            }
        }
    )
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)

    summary = engine.run(ui_state)
    engine.run_embeddings(ui_state)

    assert summary.success == 2
    assert modules.embedding_calls == [str(Path(ui_state.corpus_output_folder) / "corpus.db")] * 3
    assert engine.snapshot.stage_statuses["Embeddings"].status == "Done"
    assert engine.snapshot.stage_statuses["Embeddings"].detail == "1 embeddings generated."


def test_manual_embedding_exception_does_not_undo_document_success(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    modules = FakeModules(
        {
            "__embeddings__": {
                "embed": [
                    {"status": "completed", "count": 1, "reason": "1 embeddings generated."},
                    {"raise": RuntimeError("embedding exploded")},
                ]
            }
        }
    )
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)

    summary = engine.run(ui_state)
    engine.run_embeddings(ui_state)

    assert summary.success == 1
    assert load_single_record(tmp_path).final_disposition == "success"
    assert engine.snapshot.stage_statuses["Embeddings"].status == "Error"
    assert engine.snapshot.stage_statuses["Embeddings"].detail == "embedding exploded"
