from __future__ import annotations

import json

from .loader_page_image_support import set_source_hash, write_page_image
from corpus_builder.loader import load_from_file
from tests.fixtures.loader_io import load_input_file


def test_loader_persists_page_images_when_enabled(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    page_root = tmp_path / "page_images"
    write_page_image(page_root, vision_structured, b"page-image-1")
    json_path = make_input_pair(
        "page_blob_doc",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )

    result = load_input_file(db, json_path, persist_page_images_in_db=True, page_images_dir=page_root)

    row = db.execute(
        "SELECT page, content_type, byte_size, image_sha256, length(image_blob) AS blob_size "
        "FROM document_page_images WHERE document_id = ?",
        ("page_blob_doc",),
    ).fetchone()
    assert result.status == "loaded"
    assert row["page"] == 1
    assert row["content_type"] == "image/jpeg"
    assert row["byte_size"] == 12
    assert row["blob_size"] == 12
    assert len(row["image_sha256"]) == 64


def test_loader_infers_structured_source_for_optimizer_page_image_dirs(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    tmp_path,
):
    source_hash = "sha256:4452a9c21f0fba9d4fb9dcdc93b8e1b425e28a0e37294ebffc87863d8e933f84"
    structured_payload = set_source_hash(vision_structured, source_hash)
    structured_payload["source"] = {
        **structured_payload.get("source", {}),
        "file_name": "201611136 V - L - Reinhard Feinmechanik Dietzenbach - Anlieferung von 20 Stueck Roh.5093a384.docx",
        "file_path": "../../source/201611136 V - L - Reinhard Feinmechanik Dietzenbach - Anlieferung von 20 Stueck Roh.5093a384.docx",
    }
    normalized_payload = dict(vision_normalized)
    normalized_payload.pop("source", None)
    normalized_dir = tmp_path / "normalized"
    structured_dir = tmp_path / "structured"
    page_root = tmp_path / "page_images"
    for directory in (normalized_dir, structured_dir, page_root):
        directory.mkdir()
    normalized_path = normalized_dir / "delivery.structured.normalized.json"
    structured_path = structured_dir / "delivery.structured.json"
    validation_path = tmp_path / "delivery.vision_validation_report.json"
    normalized_path.write_text(json.dumps(normalized_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    structured_path.write_text(json.dumps(structured_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    validation_path.write_text(json.dumps(vision_validation_report, indent=2, ensure_ascii=False), encoding="utf-8")
    image_dir = page_root / "201611136 V - L - Reinhard Feinmechanik Di.f8da4514.4452a9c2"
    image_dir.mkdir()
    (image_dir / "page_001.png").write_bytes(b"png-page-image")

    result = load_from_file(db, normalized_path, validation_path, persist_page_images_in_db=True, page_images_dir=page_root)

    image_row = db.execute(
        "SELECT content_type, byte_size FROM document_page_images WHERE document_id = ?",
        ("delivery",),
    ).fetchone()
    document_row = db.execute(
        "SELECT file_name, file_path, content_hash FROM documents WHERE id = ?",
        ("delivery",),
    ).fetchone()
    assert result.status == "loaded"
    assert image_row["content_type"] == "image/png"
    assert image_row["byte_size"] == 14
    assert document_row["file_name"].endswith(".docx")
    assert document_row["file_path"].startswith("../../source/")
    assert document_row["content_hash"] == source_hash


def test_loader_persists_only_source_page_image_for_page_scoped_documents(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    source_hash = "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    structured_payload = set_source_hash(vision_structured, source_hash)
    structured_payload["source"] = {
        **structured_payload.get("source", {}),
        "file_name": "science.pdf",
        "file_path": "../../source/science.pdf::page=002-of-003",
    }
    structured_payload["classification"] = {
        **structured_payload.get("classification", {}),
        "page_count": 3,
    }
    page_root = tmp_path / "page_images"
    write_page_image(page_root, structured_payload, b"page-one", page=1)
    write_page_image(page_root, structured_payload, b"page-two-selected", page=2)
    write_page_image(page_root, structured_payload, b"page-three", page=3)
    json_path = make_input_pair("page_blob_scoped", structured_payload, vision_report=vision_validation_report)

    result = load_input_file(db, json_path, persist_page_images_in_db=True, page_images_dir=page_root)

    rows = db.execute(
        "SELECT page, byte_size, image_blob FROM document_page_images WHERE document_id = ? ORDER BY page",
        ("page_blob_scoped",),
    ).fetchall()
    assert result.status == "loaded"
    assert [(row["page"], row["byte_size"], row["image_blob"]) for row in rows] == [
        (2, 17, b"page-two-selected")
    ]
