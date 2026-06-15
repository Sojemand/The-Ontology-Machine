from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.pipeline.request_enrichment_projection import validated_projection_catalog
from tests.pipeline_harness import create_source, load_single_record, make_engine, make_ui_state


def test_image_route_builds_request_with_projection_catalog_before_interpreter_run(
    tmp_path: Path,
) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, "scan.jpg", content="image")
    interpreter_inputs: list[Path] = []

    engine = make_engine(tmp_path, scenarios={})
    original_interpret_document = engine._modules.interpret_document

    def capture_interpreter_input(
        input_path: Path,
        output_path: Path,
        *,
        module_key: str | None = None,
        interpreter_profile: str | None = None,
        debug_bundle_dir: Path | None = None,
    ):
        interpreter_inputs.append(input_path)
        return original_interpret_document(
            input_path,
            output_path,
            module_key=module_key,
            interpreter_profile=interpreter_profile,
            debug_bundle_dir=debug_bundle_dir,
        )

    engine._modules.interpret_document = capture_interpreter_input
    summary = engine.run(ui_state)

    record = load_single_record(tmp_path)
    request_payload = json.loads(Path(record.artifacts.interpreter_request_path).read_text(encoding="utf-8"))
    assert summary.success == 1
    assert record.route_family == "Documents"
    assert record.interpreter_module_key == "interpreter"
    assert record.artifacts.interpreter_request_path.endswith("requests\\scan.jpg\\interpreter.request.json")
    assert len(interpreter_inputs) == 1
    assert interpreter_inputs[0].name == "interpreter.request.json"
    assert interpreter_inputs[0].suffix != ".raw"
    assert request_payload["projection_catalog"]["release_fingerprint"] == "sha256:semantic-default"
    assert engine._modules.runtime_semantic_release_reads == [str(Path(ui_state.corpus_output_folder) / "corpus.db")]
    assert engine._modules.runtime_semantic_asset_builds == []
    assert engine._modules.normalizer_release_fingerprints == ["sha256:semantic-default"]
    assert engine._modules.extract_calls[0]["module_key"] == "optimizer"
    runtime_policy_path = Path(engine._modules.extract_calls[0]["runtime_policy_path"])
    runtime_policy_payload = json.loads(runtime_policy_path.read_text(encoding="utf-8"))
    full_runtime_payload = json.loads(runtime_policy_path.with_name("runtime_semantic_assets.json").read_text(encoding="utf-8"))
    assert runtime_policy_path.name == "optimizer_runtime_semantic_assets.json"
    assert "semantic_extraction_policy" in full_runtime_payload["vision_policy_bundle"]
    assert "semantic_extraction_policy" not in runtime_policy_payload["vision_policy_bundle"]
    assert "projection_overrides" not in runtime_policy_payload["vision_policy_bundle"]["ocr_policy"]
    assert runtime_policy_payload["vision_policy_bundle"]["ocr_policy"]["defaults"]["render"]["page_image_dpi"] == 150


def test_invalid_runtime_semantic_assets_fail_closed_before_request_enrichment(
    tmp_path: Path,
) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = make_engine(tmp_path, scenarios={})
    broken_release = engine._modules.read_active_semantic_release(Path(ui_state.corpus_output_folder) / "corpus.db")
    broken_snapshot = dict(broken_release["active_snapshot"])
    broken_snapshot["projection_catalog"] = {
        **broken_snapshot["projection_catalog"],
        "release_fingerprint": "sha256:other",
    }
    engine._modules.scenarios["__active_release__"] = {
        **broken_release,
        "active_snapshot": broken_snapshot,
    }
    with pytest.raises(RuntimeError, match="projection_catalog"):
        engine.run(ui_state)

    record = load_single_record(tmp_path)
    assert record.attempts == 0
    assert engine._modules.validated_paths == []
    assert engine.snapshot.stage_statuses["Runtime Semantics"].status == "Error"


def test_projection_catalog_rejects_non_canonical_runtime_locale() -> None:
    with pytest.raises(ValueError, match="runtime_locale must be en"):
        validated_projection_catalog(
            {
                "catalog_version": "sha256:test",
                "master_taxonomy_version": "2026-03-28.v6",
                "runtime_locale": "de",
                "projections": [],
            }
        )

