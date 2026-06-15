from __future__ import annotations

from pathlib import Path

import pytest

from .test_integrations_workflow import _modules


def test_load_document_forwards_page_image_persistence_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modules = _modules(tmp_path, "corpus_builder")
    captured: dict[str, object] = {}

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        captured["module_key"] = spec.key
        captured["payload"] = payload
        captured["timeout"] = timeout
        captured["env_overlay"] = env_overlay
        return {"status": "loaded"}

    monkeypatch.setattr("orchestrator.integrations.workflow.adapter.invoke_contract", fake_invoke)

    modules.load_document(
        tmp_path / "doc.structured.json",
        tmp_path / "doc.vision_validation_report.json",
        tmp_path / "doc.structured.normalized.json",
        tmp_path / "doc.raw.json",
        tmp_path / "corpus.db",
        persist_page_images_in_db=True,
        page_images_dir=tmp_path / "page_images" / "doc.abcd1234",
    )

    assert captured["module_key"] == "corpus_builder"
    assert captured["payload"] == {
        "action": "load_document",
        "structured_path": str(tmp_path / "doc.structured.json"),
        "validation_path": str(tmp_path / "doc.vision_validation_report.json"),
        "normalized_path": str(tmp_path / "doc.structured.normalized.json"),
        "raw_path": str(tmp_path / "doc.raw.json"),
        "corpus_db_path": str(tmp_path / "corpus.db"),
        "persist_page_images_in_db": True,
        "page_images_dir": str(tmp_path / "page_images" / "doc.abcd1234"),
    }
    assert captured["timeout"] == 600
    assert captured["env_overlay"] is None
