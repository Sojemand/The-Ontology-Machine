from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.models import DocumentRecord
import orchestrator.pipeline.artifact_repository as artifact_repository
import orchestrator.pipeline.policy as pipeline_policy
import orchestrator.pipeline.storage_repository as storage_repository
import orchestrator.pipeline.success_publication as success_publication
from orchestrator.state import load_pipeline_state
from tests.pipeline_harness import (
    artifact_root,
    create_source,
    error_case_root,
    error_root,
    load_single_record,
    make_engine,
    make_ui_state,
    orchestrator_logs_root,
    pipeline_state_path,
    route_logs_root,
    route_root,
    sha256,
)


def _load_state(tmp_path: Path):
    return load_pipeline_state(pipeline_state_path(tmp_path))


def test_success_moves_original_to_originals_archive(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    summary = make_engine(tmp_path, scenarios={}).run(ui_state)
    record = load_single_record(tmp_path)
    file_route = route_root(ui_state)

    assert summary.success == 1
    assert not source.exists()
    assert (file_route / "originals" / "doc.pdf").exists()
    assert (file_route / "requests" / "doc.pdf" / "interpreter.request.json").exists()
    assert (file_route / "structured" / "doc.pdf.structured.json").exists()
    assert (file_route / "validation" / "doc.pdf.files_validation_report.json").exists()
    assert (file_route / "normalized" / "doc.pdf.structured.normalized.json").exists()
    assert (route_logs_root(ui_state) / "doc.pdf.run.log").exists()
    assert not (artifact_root(ui_state) / "structured").exists()
    assert not (artifact_root(ui_state) / "validation").exists()
    assert not (artifact_root(ui_state) / "normalized").exists()
    assert not (artifact_root(ui_state) / "logs").exists()
    assert record.current_location == "originals_archive"
    assert "originals" in record.source_path


def test_success_preserves_relative_path_in_originals_archive(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, "subfolder/doc.pdf")
    summary = make_engine(tmp_path, scenarios={}).run(ui_state)

    assert summary.success == 1
    assert (route_root(ui_state) / "originals" / "subfolder" / "doc.pdf").exists()


def test_reset_run_history_keeps_success_artifacts_state_and_corpus(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    engine = make_engine(tmp_path, scenarios={})

    first_summary = engine.run(ui_state)
    reset_summary = engine.reset_run_history(ui_state)
    state = _load_state(tmp_path)

    assert first_summary.success == 1
    assert reset_summary.cleared_records == 0
    assert reset_summary.restored_sources == 0
    assert reset_summary.removed_targets >= 1
    assert not source.exists()
    assert route_root(ui_state).exists()
    assert (route_root(ui_state) / "originals" / "doc.pdf").exists()
    assert not error_root(ui_state).exists()
    assert (Path(ui_state.corpus_output_folder) / "corpus.db").exists()
    assert pipeline_state_path(tmp_path).exists()
    assert orchestrator_logs_root(tmp_path).exists()
    assert len(state.documents) == 1
    assert next(iter(state.documents.values())).final_disposition == "success"


def test_reset_run_history_restores_error_sources_and_preserves_success_history(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    success_source = create_source(ui_state, "ok.pdf", content="ok")
    error_source = create_source(ui_state, "bad.pdf", content="bad")
    engine = make_engine(tmp_path, {"bad.pdf": {"validate": [{"status": "FAIL"}, {"status": "FAIL"}, {"status": "FAIL"}]}})

    summary = engine.run(ui_state)
    reset_summary = engine.reset_run_history(ui_state)
    records = {record.file_name: record for record in _load_state(tmp_path).documents.values()}

    assert success_source.exists() is False
    assert summary.errors == 1
    assert summary.success == 1
    assert reset_summary.cleared_records == 1
    assert reset_summary.restored_sources == 1
    assert error_source.exists()
    assert not error_root(ui_state).exists()
    assert (route_root(ui_state) / "originals" / "ok.pdf").exists()
    assert (Path(ui_state.corpus_output_folder) / "corpus.db").exists()
    assert set(records) == {"ok.pdf"}
    assert records["ok.pdf"].final_disposition == "success"


def test_originals_archive_deduplicates_existing_matching_target(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state, content="same")
    existing = route_root(ui_state) / "originals" / "doc.pdf"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("same", encoding="utf-8")
    record = DocumentRecord(content_hash=sha256(source), file_name="doc.pdf", relative_path="doc.pdf", original_source_path=str(source), source_path=str(source), route_family="Documents")
    engine = make_engine(tmp_path, scenarios={})
    ctx = SimpleNamespace(ui_state=ui_state, managed_roots=storage_repository.managed_roots(engine, ui_state))

    artifact_repository.move_to_originals_archive(engine, record, ctx)

    assert not source.exists()
    assert existing.read_text(encoding="utf-8") == "same"
    assert record.source_path == str(existing)
    assert sorted(path.name for path in existing.parent.iterdir()) == ["doc.pdf"]


def test_originals_archive_renames_when_target_contains_other_content(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state, content="new")
    existing = route_root(ui_state) / "originals" / "doc.pdf"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old", encoding="utf-8")
    record = DocumentRecord(content_hash=sha256(source), file_name="doc.pdf", relative_path="doc.pdf", original_source_path=str(source), source_path=str(source), route_family="Documents")
    engine = make_engine(tmp_path, scenarios={})
    ctx = SimpleNamespace(ui_state=ui_state, managed_roots=storage_repository.managed_roots(engine, ui_state))

    artifact_repository.move_to_originals_archive(engine, record, ctx)

    renamed = existing.with_name(f"doc__archive_{pipeline_policy.hash8(record.content_hash)}.pdf")
    assert existing.read_text(encoding="utf-8") == "old"
    assert renamed.read_text(encoding="utf-8") == "new"
    assert record.source_path == str(renamed)
    assert not source.exists()


def test_originals_archive_deduplicates_existing_matching_conflict_target(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state, content="new")
    existing = route_root(ui_state) / "originals" / "doc.pdf"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old", encoding="utf-8")
    record = DocumentRecord(content_hash=sha256(source), file_name="doc.pdf", relative_path="doc.pdf", original_source_path=str(source), source_path=str(source), route_family="Documents")
    archived = existing.with_name(f"doc__archive_{pipeline_policy.hash8(record.content_hash)}.pdf")
    archived.write_text("new", encoding="utf-8")
    engine = make_engine(tmp_path, scenarios={})
    ctx = SimpleNamespace(ui_state=ui_state, managed_roots=storage_repository.managed_roots(engine, ui_state))

    artifact_repository.move_to_originals_archive(engine, record, ctx)

    assert existing.read_text(encoding="utf-8") == "old"
    assert archived.read_text(encoding="utf-8") == "new"
    assert not archived.with_name(f"{archived.stem}_2.pdf").exists()
    assert record.source_path == str(archived)
    assert not source.exists()


def test_published_original_target_reuses_existing_matching_conflict_target(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state, content="new")
    existing = route_root(ui_state) / "originals" / "doc.pdf"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old", encoding="utf-8")
    record = DocumentRecord(content_hash=sha256(source), file_name="doc.pdf", relative_path="doc.pdf", original_source_path=str(source), source_path=str(source), route_family="Documents")
    archived = existing.with_name(f"doc__archive_{pipeline_policy.hash8(record.content_hash)}.pdf")
    archived.write_text("new", encoding="utf-8")

    target = success_publication.published_original_target(make_engine(tmp_path, scenarios={}), record, route_root(ui_state))

    assert target == archived


def test_transient_page_retry_does_not_create_terminal_error_case_snapshot(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    summary = make_engine(tmp_path, {"doc.pdf": {"interpret": [{"status": "error", "error": "llm timeout"}, {"status": "ok"}]}}).run(ui_state)

    assert summary.success == 1
    assert not (error_case_root(ui_state, "Interpreter") / "logs" / "doc.pdf.error_manifest.json").exists()
    assert not (error_case_root(ui_state, "Interpreter") / "requests" / "doc.pdf" / "interpreter.request.json").exists()

