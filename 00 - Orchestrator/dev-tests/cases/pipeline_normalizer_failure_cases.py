from __future__ import annotations

from pathlib import Path

from tests.pipeline_harness import create_source, load_single_record, make_engine, make_ui_state, route_root


def test_normalizer_missing_output_fails_closed(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    output_path = route_root(ui_state) / "normalized" / "doc.pdf.structured.normalized.json"
    engine = make_engine(tmp_path, {"doc.pdf": {"normalize": {"status": "OK", "output_path": str(output_path), "create_normalized": False}}})

    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert "Normalizer output is missing" in load_single_record(tmp_path).last_error
    assert engine._modules.loaded_paths == []


def test_normalizer_external_output_is_rejected(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    external_output = tmp_path / "external" / "doc.structured.normalized.json"
    engine = make_engine(tmp_path, {"doc.pdf": {"normalize": {"status": "OK", "output_path": str(external_output)}}})

    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert "outside the pipeline" in load_single_record(tmp_path).last_error
    assert external_output.exists()
    assert engine._modules.loaded_paths == []


def test_corpus_success_statuses_are_final_success(tmp_path: Path) -> None:
    for status in ("loaded", "archived_and_loaded", "skipped"):
        case_root = tmp_path / status
        ui_state = make_ui_state(case_root)
        create_source(ui_state)
        assert make_engine(case_root, {"doc.pdf": {"load": {"status": status}}}).run(ui_state).success == 1
