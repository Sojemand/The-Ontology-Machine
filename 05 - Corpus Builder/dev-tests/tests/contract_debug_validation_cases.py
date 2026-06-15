from __future__ import annotations

from pathlib import Path

import pytest

from corpus_builder.context import ModuleContext
from corpus_builder.models import LoadBatchResult, LoadResult
from corpus_builder.orchestrator_contract import validation
from .contract_debug_support import dispatch


def test_validation_rejects_irrelevant_debug_fields(tmp_path: Path) -> None:
    source_path = tmp_path / "doc.structured.normalized.json"
    source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unbekannte Felder: worker_count"):
        validation.parse_debug_run_command(
            {
                "action": "debug_run",
                "mode": "single",
                "session_root": str(tmp_path / "session"),
                "output_root": str(tmp_path / "session" / "outputs"),
                "source_path": str(source_path),
                "worker_count": 2,
            }
        )


def test_validation_accepts_page_image_persistence_option(tmp_path: Path) -> None:
    source_path = tmp_path / "doc.structured.normalized.json"
    source_path.write_text("{}", encoding="utf-8")

    command = validation.parse_debug_run_command(
        {
            "action": "debug_run",
            "mode": "single",
            "session_root": str(tmp_path / "session"),
            "output_root": str(tmp_path / "session" / "outputs"),
            "source_path": str(source_path),
            "options": {"persist_page_images_in_db": True},
        }
    )

    assert command.persist_page_images_in_db is True


def test_load_document_passes_page_image_options_to_load_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = ModuleContext(tmp_path)
    captured: dict[str, object] = {}

    def fake_load_batch(_context, bundles, *, persist_page_images_in_db=None, page_images_dir=None):
        captured["persist_page_images_in_db"] = persist_page_images_in_db
        captured["page_images_dir"] = page_images_dir
        captured["bundle_count"] = len(bundles)
        return LoadBatchResult(loaded=1, results=[LoadResult(status="loaded", document_id="doc-1")])

    monkeypatch.setattr("corpus_builder.orchestrator_contract.workflow.load_batch", fake_load_batch)

    response = dispatch(
        context,
        {
            "action": "load_document",
            "corpus_db_path": str(tmp_path / "corpus.db"),
            "normalized_path": str(tmp_path / "doc.structured.normalized.json"),
            "structured_path": str(tmp_path / "doc.structured.json"),
            "validation_path": str(tmp_path / "doc.vision_validation_report.json"),
            "raw_path": str(tmp_path / "doc.raw.json"),
            "persist_page_images_in_db": True,
            "page_images_dir": str(tmp_path / "page_images" / "doc.abcd1234"),
        },
    )

    assert response["status"] == "loaded"
    assert captured == {
        "persist_page_images_in_db": True,
        "page_images_dir": str(tmp_path / "page_images" / "doc.abcd1234"),
        "bundle_count": 1,
    }
