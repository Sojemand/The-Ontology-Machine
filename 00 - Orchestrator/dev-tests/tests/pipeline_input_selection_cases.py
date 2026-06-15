from __future__ import annotations

from pathlib import Path

from orchestrator.state import load_pipeline_state
from tests.pipeline_harness import (
    create_source,
    error_root,
    load_single_record,
    make_engine,
    make_ui_state,
    pipeline_state_path,
    route_root,
    saved_record,
    sha256,
    write_saved_state,
)


def test_single_file_mode_uses_alphabetically_first_pending_file(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path, mode="single")
    source_b = create_source(ui_state, "b.pdf", content="b")
    source_a = create_source(ui_state, "a.pdf", content="a")
    a_hash = sha256(source_a)
    b_hash = sha256(source_b)
    engine = make_engine(tmp_path, scenarios={})

    summary = engine.run(ui_state)

    state = load_pipeline_state(pipeline_state_path(tmp_path))
    assert summary.total == 1
    assert state.documents[a_hash].final_disposition == "success"
    assert state.documents[b_hash].attempts == 0


def test_input_folder_inside_artifact_root_is_processed(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    input_root = Path(ui_state.artifact_folder) / "Input"
    input_root.mkdir(parents=True)
    ui_state.input_folder = str(input_root)
    create_source(ui_state, "inside-artifacts.txt", content="story")

    summary = make_engine(tmp_path, scenarios={}).run(ui_state)

    assert summary.success == 1
    assert (route_root(ui_state) / "originals" / "inside-artifacts.txt").exists()


def test_kernel_owned_run_ignores_unconfirmed_error_case_retry_records(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    active_source = create_source(ui_state, "active.pdf", content="active")
    active_hash = sha256(active_source)
    retry_source = error_root(ui_state) / "Validator" / "Documents" / "originals" / "retry.pdf"
    retry_source.parent.mkdir(parents=True)
    retry_source.write_text("retry", encoding="utf-8")
    retry_hash = sha256(retry_source)
    write_saved_state(
        tmp_path,
        saved_record(
            retry_hash,
            file_name="retry.pdf",
            relative_path="retry.pdf",
            original_source_path=str(Path(ui_state.input_folder) / "retry.pdf"),
            source_path=str(retry_source),
            current_location="error_bundle",
            status="error",
            final_disposition="",
            attempts=2,
            failed_attempts=1,
            last_stage="Validator",
        ),
    )
    engine = make_engine(tmp_path, scenarios={})

    summary = engine.run(ui_state, owner_input_hashes={active_hash})
    state = load_pipeline_state(pipeline_state_path(tmp_path))

    assert summary.total == 1
    assert summary.success == 1
    assert state.documents[active_hash].final_disposition == "success"
    assert state.documents[retry_hash].current_location == "error_bundle"
    assert state.documents[retry_hash].attempts == 2


def test_processed_file_is_reprocessed_after_workspace_change(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state, "story.txt", content="same story")
    content_hash = sha256(source)
    old_artifact_root = tmp_path / "old-artifacts"
    old_structured = old_artifact_root / "Documents" / "structured" / "story.structured.json"
    write_saved_state(
        tmp_path,
        saved_record(
            content_hash,
            file_name="story.txt",
            relative_path="story.txt",
            original_source_path=str(tmp_path / "old-input" / "story.txt"),
            source_path=str(old_artifact_root / "Documents" / "originals" / "story.txt"),
            current_location="originals_archive",
            status="success",
            final_disposition="success",
            attempts=1,
            failed_attempts=0,
            last_stage="Corpus Builder",
            artifacts={"structured_paths": [str(old_structured)], "structured_path": str(old_structured)},
        ),
    )

    summary = make_engine(tmp_path, scenarios={}).run(ui_state)
    record = load_single_record(tmp_path)

    assert summary.success == 1
    assert record.attempts == 1
    assert record.source_path.startswith(str(route_root(ui_state) / "originals"))
