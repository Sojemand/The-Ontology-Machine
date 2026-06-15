from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import OrchestratorEngine
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import create_source, load_single_record, make_ui_state, route_root, runtime_files

from .pipeline_normalizer_review_support import (
    _is_runtime_normalized_path,
    _is_runtime_structured_path,
    _is_runtime_validation_input,
)


def test_success_uses_canonical_structured_copy_for_validation_and_load(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    modules = FakeModules({})
    summary = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules).run(ui_state)

    assert summary.success == 1
    assert len(modules.validated_paths) == 1
    assert _is_runtime_validation_input(modules.validated_paths[0])
    assert len(modules.loaded_paths) == 1
    assert _is_runtime_structured_path(modules.loaded_paths[0])
    assert len(modules.loaded_normalized_paths) == 1
    assert _is_runtime_normalized_path(modules.loaded_normalized_paths[0])
    record = load_single_record(tmp_path)
    assert Path(record.artifacts.structured_path).exists()
    assert Path(record.artifacts.normalized_path).exists()
    assert runtime_files(tmp_path) == []


def test_same_named_inputs_keep_distinct_structured_outputs(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, "a/doc.pdf", content="a")
    create_source(ui_state, "b/doc.pdf", content="b")
    modules = FakeModules({})
    summary = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules).run(ui_state)

    structured_root = route_root(ui_state) / "structured"
    expected = {
        str(structured_root / "a" / "doc.pdf.structured.json"),
        str(structured_root / "b" / "doc.pdf.structured.json"),
    }
    actual_files = {str(path) for path in structured_root.rglob("*.structured.json")}
    assert summary.success == 2
    assert actual_files == expected
    assert len(modules.validated_paths) == 2
    assert all(_is_runtime_validation_input(path) for path in modules.validated_paths)
    assert len(set(modules.validated_paths)) == 2
    assert len(set(modules.loaded_paths)) == 2
    assert all(_is_runtime_structured_path(path) for path in modules.loaded_paths)
