from __future__ import annotations

from pathlib import Path

from tests.pipeline_harness import (
    artifact_root,
    create_source,
    load_single_record,
    make_engine,
    make_ui_state,
    route_root,
    run_log_files,
    runtime_files,
    sha256,
)


def test_success_keeps_optimizer_outputs_and_cleans_temp_outputs(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    content_hash = sha256(source)
    engine = make_engine(tmp_path, scenarios={})
    summary = engine.run(ui_state)

    files_root = route_root(ui_state)
    assert summary.success == 1
    assert list((files_root / "raw_extracts").glob("*.raw.json"))
    assert not (files_root / "archive").exists()
    assert not (files_root / "claim_tokens").exists()
    assert list((files_root / "page_images").rglob("page_001.jpg"))
    assert (files_root / "requests" / "doc.pdf" / "ocr.request.json").exists()
    assert (files_root / "requests" / "doc.pdf" / "interpreter.request.json").exists()
    assert (files_root / "requests" / "doc.pdf" / "normalizer.request.json").exists()
    assert list((files_root / "structured").glob("*.structured.json"))
    assert list((files_root / "normalized").glob("*.structured.normalized.json"))
    assert not (artifact_root(ui_state) / "structured").exists()
    assert not (artifact_root(ui_state) / "normalized").exists()
    record = load_single_record(tmp_path)
    assert record.route_family == "Documents"
    assert record.optimizer_module_key == "optimizer"
    assert record.interpreter_module_key == "interpreter"
    assert record.artifacts.optimizer_ocr_request_path.endswith("requests\\doc.pdf\\ocr.request.json")
    assert record.artifacts.interpreter_request_path.endswith("requests\\doc.pdf\\interpreter.request.json")
    assert record.artifacts.normalizer_request_path.endswith("requests\\doc.pdf\\normalizer.request.json")
    assert engine._modules.loaded_page_image_persistence_flags == [True]
    assert engine._modules.loaded_page_images_dirs[0].endswith("page_assets\\doc.pdf." + content_hash.replace("sha256:", "")[:8])
    assert len(run_log_files(tmp_path)) == 1
    assert "Run " in run_log_files(tmp_path)[0].read_text(encoding="utf-8")
    assert runtime_files(tmp_path) == []


def test_empty_raw_output_fails_closed_before_interpreter_runs(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = make_engine(tmp_path, {"doc.pdf": {"extract": {"status": "ok", "raw_path": "", "create_raw": False}}})

    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert summary.retries == 2
    assert "did not provide raw output" in load_single_record(tmp_path).last_error
    assert engine._modules.validated_paths == []


def test_missing_raw_output_file_fails_closed(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    missing_raw = route_root(ui_state) / "raw_extracts" / "doc.pdf.raw.json"
    engine = make_engine(tmp_path, {"doc.pdf": {"extract": {"status": "ok", "raw_path": str(missing_raw), "create_raw": False}}})

    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert "Optimizer output is missing" in load_single_record(tmp_path).last_error
    assert engine._modules.validated_paths == []


def test_external_raw_output_is_rejected(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    external_raw = tmp_path / "external" / "doc.raw.json"
    engine = make_engine(tmp_path, {"doc.pdf": {"extract": {"status": "ok", "raw_path": str(external_raw)}}})

    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert "outside the pipeline" in load_single_record(tmp_path).last_error
    assert external_raw.exists()
    assert engine._modules.validated_paths == []
