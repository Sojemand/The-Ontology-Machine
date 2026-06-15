from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.locking import FileLock
from orchestrator.models import DocumentRecord
from orchestrator.pipeline import OrchestratorEngine
import orchestrator.pipeline.bundle_repository as bundle_repository
import orchestrator.pipeline.storage_repository as storage_repository
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import (
    artifact_root,
    create_source,
    error_case_root,
    error_root,
    legacy_error_root,
    lock_path,
    make_engine,
    make_ui_state,
    route_root,
    saved_record,
    sha256,
    write_saved_state,
)


def test_restart_resume_reprocesses_existing_error_bundle(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    bundled_source = legacy_error_root(ui_state) / "Documents" / "Interpreter" / "doc.pdf.00000000" / "source" / "doc.pdf"
    bundled_source.parent.mkdir(parents=True, exist_ok=True)
    bundled_source.write_text("doc", encoding="utf-8")
    source.unlink()
    write_saved_state(tmp_path, saved_record(sha256(bundled_source), original_source_path=str(source), source_path=str(bundled_source)))

    summary = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=FakeModules({"doc.pdf": {"interpret": {"status": "ok"}}})).run(ui_state)

    assert summary.success == 1
    assert (route_root(ui_state) / "originals" / "doc.pdf").exists()


def test_restart_resume_reprocesses_existing_error_case_bundle(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    bundled_source = error_case_root(ui_state, "Validator") / "originals" / "doc.pdf"
    bundled_source.parent.mkdir(parents=True, exist_ok=True)
    bundled_source.write_text("doc", encoding="utf-8")
    source.unlink()
    write_saved_state(
        tmp_path,
        saved_record(
            sha256(bundled_source),
            original_source_path=str(source),
            source_path=str(bundled_source),
            current_location="error_bundle",
            final_disposition="",
            artifacts={"bundle_dir": str(error_case_root(ui_state, "Validator"))},
        ),
    )

    summary = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=FakeModules({"doc.pdf": {"interpret": {"status": "ok"}}})).run(ui_state)

    assert summary.success == 1
    assert (route_root(ui_state) / "originals" / "doc.pdf").exists()


def test_restart_resume_reprocesses_existing_processing_bundle(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    bundled_source = legacy_error_root(ui_state) / "Documents" / "Interpreter" / "doc.pdf.00000000" / "source" / "doc.pdf"
    bundled_source.parent.mkdir(parents=True, exist_ok=True)
    bundled_source.write_text("doc", encoding="utf-8")
    source.unlink()
    write_saved_state(tmp_path, saved_record(sha256(bundled_source), original_source_path=str(source), source_path=str(bundled_source), status="processing", last_error=""))

    summary = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=FakeModules({"doc.pdf": {"interpret": {"status": "ok"}}})).run(ui_state)

    assert summary.success == 1
    assert (route_root(ui_state) / "originals" / "doc.pdf").exists()


def test_reset_run_history_ignores_external_artifact_paths(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    outside = tmp_path / "outside_to_delete"
    outside.mkdir()
    (outside / "sentinel.txt").write_text("x", encoding="utf-8")
    write_saved_state(tmp_path, saved_record("sha256:test", artifacts={"bundle_dir": str(outside)}))

    make_engine(tmp_path, scenarios={}).reset_run_history(ui_state)

    assert outside.exists()
    assert (outside / "sentinel.txt").exists()


def test_reset_run_history_ignores_external_restore_paths(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    outside_current = tmp_path / "outside_current.pdf"
    outside_current.write_text("x", encoding="utf-8")
    outside_target = tmp_path / "outside_target.pdf"
    write_saved_state(
        tmp_path,
        saved_record("sha256:test", original_source_path=str(outside_target), source_path=str(outside_current)),
    )

    make_engine(tmp_path, scenarios={}).reset_run_history(ui_state)

    assert outside_current.exists()
    assert not outside_target.exists()


def test_success_archive_sanitizes_corrupted_relative_path(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    bundled_file = legacy_error_root(ui_state) / "Documents" / "Interpreter" / "doc.bundle" / "source" / "doc.pdf"
    bundled_file.parent.mkdir(parents=True, exist_ok=True)
    bundled_file.write_text("doc", encoding="utf-8")
    write_saved_state(
        tmp_path,
        saved_record(
            sha256(bundled_file),
            relative_path="../escaped/doc.pdf",
            original_source_path=str(Path(ui_state.input_folder) / "doc.pdf"),
            source_path=str(bundled_file),
            artifacts={"bundle_dir": str(bundled_file.parent.parent)},
        ),
    )

    summary = make_engine(tmp_path, scenarios={}).run(ui_state)

    assert summary.success == 1
    assert (route_root(ui_state) / "originals" / "doc.pdf").exists()
    assert not (artifact_root(ui_state) / "escaped").exists()
