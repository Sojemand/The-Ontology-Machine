from __future__ import annotations

from pathlib import Path

from tests.pipeline_harness import create_source, load_single_record, make_engine, make_ui_state


def _is_runtime_raw_path(path: str) -> bool:
    candidate = Path(path)
    return candidate.name.endswith(".raw.json") and candidate.parent.name == "raw_extracts" and candidate.parent.parent.name == "artifacts"


def test_files_route_passes_optimizer_raw_path_to_validator(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    engine = make_engine(tmp_path, scenarios={})
    create_source(ui_state)

    summary = engine.run(ui_state)
    record = load_single_record(tmp_path)

    assert summary.success == 1
    assert len(engine._modules.validator_raw_paths) == 1
    assert _is_runtime_raw_path(engine._modules.validator_raw_paths[0])
    assert record.artifacts.optimizer_raw_paths[0].endswith("Documents\\raw_extracts\\doc.pdf.raw.json")


def test_validator_fails_closed_when_raw_disappears_after_interpreter(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    engine = make_engine(tmp_path, scenarios={})
    create_source(ui_state)
    original = engine._modules.interpret_document

    def interpret_then_drop_raw(
        request_path: Path,
        output_path: Path,
        *,
        module_key: str | None = None,
        interpreter_profile: str | None = None,
        debug_bundle_dir: Path | None = None,
    ):
        result = original(
            request_path,
            output_path,
            module_key=module_key,
            interpreter_profile=interpreter_profile,
            debug_bundle_dir=debug_bundle_dir,
        )
        Path(load_single_record(tmp_path).artifacts.optimizer_raw_paths[0]).unlink()
        return result

    engine._modules.interpret_document = interpret_then_drop_raw
    summary = engine.run(ui_state)

    assert summary.errors == 1
    assert "Optimizer raw output is missing" in load_single_record(tmp_path).last_error
    assert engine._modules.validated_paths == []
    assert engine._modules.validator_raw_paths == []

