from __future__ import annotations

import json
from pathlib import Path

import pytest

from corpus_builder.context import ModuleContext
from corpus_builder.models import LoadBatchResult, LoadResult
from .contract_debug_support import dispatch, write_active_release, write_json, write_pipeline_record


def test_scan_debug_input_writes_preview_session_artifacts(tmp_path: Path, vision_structured, vision_validation_report, vision_normalized) -> None:
    context = ModuleContext(tmp_path)
    pipeline_root = tmp_path / "pipeline"
    write_pipeline_record(
        pipeline_root,
        base_name="invoice.pdf",
        vision_structured=vision_structured,
        vision_validation_report=vision_validation_report,
        vision_normalized=vision_normalized,
    )

    session_root = tmp_path / "session"
    response = dispatch(context, {"action": "scan_debug_input", "mode": "scan", "session_root": str(session_root), "input_root": str(pipeline_root)})

    preview = json.loads((session_root / "outputs" / "preview_report.json").read_text(encoding="utf-8"))
    result = json.loads((session_root / "result.json").read_text(encoding="utf-8"))
    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))

    assert response["status"] == "ok"
    assert preview["bundle_count"] == 1
    assert preview["projection_preview"][0]["projection_id"] == "housing.default.v1"
    assert result["outputs"]["preview_report"] == ["outputs/preview_report.json"]
    assert snapshot["counters"]["bundle_count"] == 1


def test_debug_run_single_writes_corpus_outputs_and_sidecar_preview(tmp_path: Path, vision_structured, vision_validation_report, vision_normalized) -> None:
    context = ModuleContext(tmp_path)
    write_active_release(context)
    pipeline_root = tmp_path / "pipeline"
    normalized_path = write_pipeline_record(
        pipeline_root,
        base_name="invoice.pdf",
        vision_structured=vision_structured,
        vision_validation_report=vision_validation_report,
        vision_normalized=vision_normalized,
    )

    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    response = dispatch(
        context,
        {
            "action": "debug_run",
            "mode": "single",
            "session_root": str(session_root),
            "output_root": str(output_root),
            "input_root": str(normalized_path.parent),
            "source_path": str(normalized_path),
        },
    )

    preview = json.loads((output_root / "preview_report.json").read_text(encoding="utf-8"))
    load_report = json.loads((output_root / "load_report.json").read_text(encoding="utf-8"))

    assert response["status"] == "ok"
    assert (output_root / "corpus.db").exists()
    assert preview["bundle_count"] == 1
    assert preview["structured_dirs"] == [str(pipeline_root / "structured")]
    assert load_report["loaded"] == 1
    assert load_report["results"][0]["status"] == "loaded"
    assert response["outputs"]["corpus_db"] == ["outputs/corpus.db"]


def test_debug_run_batch_blocks_incompatible_projection_before_db_reset(tmp_path: Path, vision_normalized) -> None:
    context = ModuleContext(tmp_path)
    write_active_release(context, projection_id="housing.default.v1")
    pipeline_root = tmp_path / "pipeline"
    normalized_dir = pipeline_root / "normalized"
    broken = dict(vision_normalized)
    broken["projection"] = dict(vision_normalized["projection"])
    broken["projection"]["projection_id"] = "missing.projection.v1"
    write_json(normalized_dir / "broken.pdf.structured.normalized.json", broken)
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    output_root.mkdir(parents=True)
    (output_root / "corpus.db").write_text("keep-me", encoding="utf-8")

    response = dispatch(context, {"action": "debug_run", "mode": "batch", "session_root": str(session_root), "output_root": str(output_root), "input_root": str(pipeline_root)})

    assert response["status"] == "error"
    assert "Rebuild abgebrochen" in response["error"]
    assert (output_root / "corpus.db").read_text(encoding="utf-8") == "keep-me"


def test_debug_run_batch_cancelled_keeps_partial_outputs(tmp_path: Path, vision_structured, vision_validation_report, vision_normalized, monkeypatch: pytest.MonkeyPatch) -> None:
    context = ModuleContext(tmp_path)
    write_active_release(context)
    pipeline_root = tmp_path / "pipeline"
    for name in ("a", "b"):
        write_pipeline_record(
            pipeline_root,
            base_name=f"{name}.pdf",
            subdir="",
            vision_structured=vision_structured,
            vision_validation_report=vision_validation_report,
            vision_normalized=vision_normalized,
        )
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    seen = {"calls": 0}

    def fake_load_batch(_context, bundles, *, persist_page_images_in_db=None):
        assert persist_page_images_in_db is False
        seen["calls"] += 1
        Path(bundles[0].corpus_db_path).write_text("db", encoding="utf-8")
        if seen["calls"] == 1:
            (session_root / "cancel.request").touch()
        return LoadBatchResult(loaded=1, results=[LoadResult(status="loaded", document_id=f"doc-{seen['calls']}")])

    monkeypatch.setattr("corpus_builder.orchestrator_contract.debug_workflow.load_batch", fake_load_batch)

    response = dispatch(context, {"action": "debug_run", "mode": "batch", "session_root": str(session_root), "output_root": str(output_root), "input_root": str(pipeline_root)})

    load_report = json.loads((output_root / "load_report.json").read_text(encoding="utf-8"))
    assert response["status"] == "cancelled"
    assert load_report["loaded"] == 1
    assert response["outputs"]["corpus_db"] == ["outputs/corpus.db"]


def test_debug_run_passes_page_image_override_to_load_batch(tmp_path: Path, vision_structured, vision_validation_report, vision_normalized, monkeypatch: pytest.MonkeyPatch) -> None:
    context = ModuleContext(tmp_path)
    write_active_release(context)
    pipeline_root = tmp_path / "pipeline"
    normalized_path = write_pipeline_record(
        pipeline_root,
        base_name="invoice.pdf",
        vision_structured=vision_structured,
        vision_validation_report=vision_validation_report,
        vision_normalized=vision_normalized,
    )
    captured: dict[str, object] = {}

    def fake_load_batch(_context, bundles, *, persist_page_images_in_db=None):
        captured["persist_page_images_in_db"] = persist_page_images_in_db
        Path(bundles[0].corpus_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(bundles[0].corpus_db_path).write_text("db", encoding="utf-8")
        return LoadBatchResult(loaded=1, results=[LoadResult(status="loaded", document_id="doc-1")])

    monkeypatch.setattr("corpus_builder.orchestrator_contract.debug_workflow.load_batch", fake_load_batch)

    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    response = dispatch(
        context,
        {
            "action": "debug_run",
            "mode": "single",
            "session_root": str(session_root),
            "output_root": str(output_root),
            "input_root": str(normalized_path.parent),
            "source_path": str(normalized_path),
            "options": {"persist_page_images_in_db": True},
        },
    )

    assert response["status"] == "ok"
    assert captured["persist_page_images_in_db"] is True
