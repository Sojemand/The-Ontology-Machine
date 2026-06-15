from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .services_artifact_rebuild_support import write_active_release, write_default_config, write_json_artifact
from corpus_builder.context import ModuleContext
from corpus_builder.standalone_artifacts import rebuild_corpus_from_artifacts


def test_rebuild_corpus_from_artifacts_replaces_existing_db_and_loads_documents(
    tmp_path: Path,
    vision_structured,
    vision_validation_report,
    vision_normalized,
):
    context = ModuleContext(tmp_path)
    context.ensure_runtime_dirs()
    write_default_config(context)
    write_active_release(context)

    pipeline_root = tmp_path / "pipeline"
    normalized_dir = pipeline_root / "normalized"
    structured_dir = pipeline_root / "structured"
    validation_dir = pipeline_root / "validation"
    write_json_artifact(normalized_dir / "invoice.pdf.structured.normalized.json", vision_normalized)
    write_json_artifact(structured_dir / "invoice.pdf.structured.json", vision_structured)
    write_json_artifact(validation_dir / "invoice.pdf.vision_validation_report.json", vision_validation_report)

    db_path = tmp_path / "corpus.db"
    db_path.write_text("stale", encoding="utf-8")

    result = rebuild_corpus_from_artifacts(
        context,
        pipeline_root=pipeline_root,
        corpus_db_path=db_path,
        replace_existing=True,
    )

    assert result["replaced_existing"] is True
    assert result["result"].loaded == 1


def test_rebuild_corpus_from_artifacts_persists_raw_payload_layer(
    tmp_path: Path,
    vision_structured,
    vision_validation_report,
    vision_normalized,
):
    context = ModuleContext(tmp_path)
    context.ensure_runtime_dirs()
    write_active_release(context)

    pipeline_root = tmp_path / "pipeline"
    write_json_artifact(pipeline_root / "normalized" / "invoice.pdf.structured.normalized.json", vision_normalized)
    write_json_artifact(pipeline_root / "structured" / "invoice.pdf.structured.json", vision_structured)
    write_json_artifact(pipeline_root / "validation" / "invoice.pdf.vision_validation_report.json", vision_validation_report)
    write_json_artifact(
        pipeline_root / "raw_extracts" / "invoice.pdf.raw.json",
        {
            "doc": {"file_name": "invoice.pdf"},
            "ctx": {"invoice_date": "2023-06-27", "total_amount": 318.79},
            "guardrail": {"sections": [{"id": "source_p01_c00", "text": "Zu zahlender Betrag 318,79 EUR"}]},
        },
    )

    db_path = tmp_path / "corpus.db"
    result = rebuild_corpus_from_artifacts(
        context,
        pipeline_root=pipeline_root,
        corpus_db_path=db_path,
        replace_existing=False,
    )

    assert result["result"].loaded == 1
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        payload = conn.execute(
            "SELECT raw_json FROM document_payloads WHERE document_id = ?",
            ("invoice.pdf",),
        ).fetchone()
        assert payload is not None
        assert json.loads(payload["raw_json"])["ctx"]["total_amount"] == 318.79
    finally:
        conn.close()


def test_rebuild_corpus_from_artifacts_persists_published_page_images(
    tmp_path: Path,
    vision_structured,
    vision_validation_report,
    vision_normalized,
):
    context = ModuleContext(tmp_path)
    context.ensure_runtime_dirs()
    write_active_release(context)

    source_hash = "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    structured_payload = dict(vision_structured)
    structured_payload["source"] = {
        **dict(vision_structured.get("source") or {}),
        "file_name": "story.odt",
        "file_path": "../../source/story.odt::page=001-of-002",
        "content_hash": source_hash,
    }
    structured_payload["classification"] = {
        **dict(vision_structured.get("classification") or {}),
        "page_count": 2,
    }
    normalized_payload = dict(vision_normalized)
    normalized_payload.pop("source", None)
    normalized_payload["classification"] = {
        **dict(vision_normalized.get("classification") or {}),
        "page_count": 2,
    }

    pipeline_root = tmp_path / "pipeline"
    write_json_artifact(pipeline_root / "normalized" / "story.odt.p001.of002.structured.normalized.json", normalized_payload)
    write_json_artifact(pipeline_root / "structured" / "story.odt.p001.of002.structured.json", structured_payload)
    write_json_artifact(pipeline_root / "validation" / "story.odt.p001.of002.vision_validation_report.json", vision_validation_report)
    page_image_dir = pipeline_root / "page_images" / "story.odt.assetcafe"
    page_image_dir.mkdir(parents=True)
    (page_image_dir / "page_001.png").write_bytes(b"published-page-one")
    (page_image_dir / "page_002.png").write_bytes(b"published-page-two")

    db_path = tmp_path / "corpus.db"
    result = rebuild_corpus_from_artifacts(
        context,
        pipeline_root=pipeline_root,
        corpus_db_path=db_path,
        replace_existing=True,
    )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT page, content_type, image_blob FROM document_page_images ORDER BY page"
        ).fetchall()
    finally:
        conn.close()
    assert result["result"].loaded == 1
    assert [(row["page"], row["content_type"], row["image_blob"]) for row in rows] == [
        (1, "image/png", b"published-page-one")
    ]
