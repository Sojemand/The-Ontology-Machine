from __future__ import annotations

from pathlib import Path

from tests.pipeline_harness import create_source, make_engine, make_ui_state, saved_record, sha256, write_saved_state
from tests.pipeline_input_flow_support import insert_corpus_hash


def test_success_record_skips_only_when_hash_exists_in_selected_db(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state, "story.txt", content="same story")
    content_hash = sha256(source)
    insert_corpus_hash(Path(ui_state.selected_corpus_db_path), content_hash)
    write_saved_state(
        tmp_path,
        saved_record(
            content_hash,
            file_name="story.txt",
            relative_path="story.txt",
            original_source_path=str(source),
            source_path=str(source),
            current_location="input",
            status="success",
            final_disposition="success",
            attempts=1,
            failed_attempts=0,
            last_stage="Corpus Builder",
        ),
    )
    engine = make_engine(tmp_path, scenarios={})

    summary = engine.run(ui_state)

    assert summary.total == 0
    assert engine._modules.loaded_paths == []


def test_success_record_reprocesses_when_hash_is_missing_from_selected_db(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state, "story.txt", content="same story")
    content_hash = sha256(source)
    insert_corpus_hash(Path(ui_state.selected_corpus_db_path), "sha256:other")
    write_saved_state(
        tmp_path,
        saved_record(
            content_hash,
            file_name="story.txt",
            relative_path="story.txt",
            original_source_path=str(source),
            source_path=str(source),
            current_location="input",
            status="success",
            final_disposition="success",
            attempts=1,
            failed_attempts=0,
            last_stage="Corpus Builder",
        ),
    )
    engine = make_engine(tmp_path, scenarios={})

    summary = engine.run(ui_state)

    assert summary.success == 1
    assert engine._modules.loaded_paths


def test_success_record_reprocesses_when_selected_db_has_only_archived_hash(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state, "story.txt", content="same story")
    content_hash = sha256(source)
    insert_corpus_hash(Path(ui_state.selected_corpus_db_path), content_hash, archived=True)
    write_saved_state(
        tmp_path,
        saved_record(
            content_hash,
            file_name="story.txt",
            relative_path="story.txt",
            original_source_path=str(source),
            source_path=str(source),
            current_location="input",
            status="success",
            final_disposition="success",
            attempts=1,
            failed_attempts=0,
            last_stage="Corpus Builder",
        ),
    )
    engine = make_engine(tmp_path, scenarios={})

    summary = engine.run(ui_state)

    assert summary.success == 1
    assert engine._modules.loaded_paths
