from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import OrchestratorEngine
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import create_source, error_case_root, load_single_record, make_engine, make_ui_state, route_root, runtime_files

from .pipeline_normalizer_review_support import _is_runtime_structured_path, _is_runtime_validation_input


def test_normalizer_review_passes_without_retry_and_keeps_reason(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    modules = FakeModules({"doc.pdf": {"normalize": {"status": "OK", "needs_review": True, "message": "normalized", "review_reason": "Unclear classification"}}})
    summary = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules).run(ui_state)
    record = load_single_record(tmp_path)
    assert summary.errors == 0
    assert summary.success == 1
    assert summary.needs_review == 1
    assert summary.retries == 0
    assert record.last_stage == "Corpus Builder"
    assert record.normalizer_failed_attempts == 0
    assert record.interpreter_needs_review is False
    assert record.normalizer_needs_review is True
    assert record.normalizer_review_reason == "Unclear classification"
    assert record.review_reason == "Unclear classification"
    assert record.last_error == ""
    assert record.final_disposition == "needs_review"
    assert record.status == "success"
    assert record.current_location == "originals_archive"
    assert len(modules.validated_paths) == 1
    assert _is_runtime_validation_input(modules.validated_paths[0])
    assert len(modules.normalized_paths) == 1
    assert all(_is_runtime_structured_path(path) for path in modules.normalized_paths)
    assert len(modules.loaded_paths) == 1
    assert all(_is_runtime_structured_path(path) for path in modules.loaded_paths)
    assert Path(record.source_path).exists()
    assert Path(record.artifacts.normalized_path).exists()
    assert not (error_case_root(ui_state, "Normalizer") / "logs" / "doc.pdf.error_manifest.json").exists()
    assert runtime_files(tmp_path) == []


def test_normalizer_review_publishes_success_artifacts_instead_of_error_bundle(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    modules = FakeModules({"doc.pdf": {"normalize": {"status": "OK", "needs_review": True, "message": "normalized", "review_reason": "Normalizer review"}}})
    summary = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules).run(ui_state)
    record = load_single_record(tmp_path)
    file_route = route_root(ui_state)

    assert summary.errors == 0
    assert summary.success == 1
    assert summary.needs_review == 1
    assert record.final_disposition == "needs_review"
    assert record.last_stage == "Corpus Builder"
    assert record.normalizer_failed_attempts == 0
    assert record.normalizer_needs_review is True
    assert record.normalizer_review_reason == "Normalizer review"
    assert record.review_reason == "Normalizer review"
    assert record.current_location == "originals_archive"
    assert len(modules.validated_paths) == 1
    assert _is_runtime_validation_input(modules.validated_paths[0])
    assert len(modules.normalized_paths) == 1
    assert all(_is_runtime_structured_path(path) for path in modules.normalized_paths)
    assert len(modules.loaded_paths) == 1
    assert not (error_case_root(ui_state, "Normalizer") / "logs" / "doc.pdf.error_manifest.json").exists()
    assert (file_route / "logs" / "doc.pdf.run.log").exists()
    assert (file_route / "originals" / "doc.pdf").exists()
    assert (file_route / "raw_extracts" / "doc.pdf.raw.json").exists()
    published_page_images = sorted(path.name for path in (file_route / "page_images").rglob("*") if path.is_file())
    assert published_page_images == ["page_001.jpg"]
    assert Path(record.artifacts.interpreter_request_path).exists()
    assert Path(record.artifacts.structured_path).exists()
    assert Path(record.artifacts.validation_report_path).exists()
    assert Path(record.artifacts.normalized_path).exists()
    assert runtime_files(tmp_path) == []
