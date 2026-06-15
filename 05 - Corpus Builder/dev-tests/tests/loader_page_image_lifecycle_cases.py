from __future__ import annotations

import json

from .loader_page_image_support import set_source_hash, write_page_image
from tests.fixtures.loader_io import load_input_file


def test_loader_keeps_existing_document_flow_without_page_image_persistence(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    page_root = tmp_path / "page_images"
    write_page_image(page_root, vision_structured, b"page-image-1")
    json_path = make_input_pair("page_blob_off", vision_structured, vision_report=vision_validation_report)

    result = load_input_file(db, json_path, page_images_dir=page_root)

    assert result.status == "loaded"
    assert db.execute("SELECT COUNT(*) FROM document_page_images").fetchone()[0] == 0


def test_loader_tolerates_missing_page_images_when_enabled(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    json_path = make_input_pair("page_blob_missing", vision_structured, vision_report=vision_validation_report)

    result = load_input_file(
        db,
        json_path,
        persist_page_images_in_db=True,
        page_images_dir=tmp_path / "missing-page-images",
    )

    assert result.status == "loaded"
    assert db.execute("SELECT COUNT(*) FROM document_page_images").fetchone()[0] == 0


def test_loader_skips_page_images_over_size_limit(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    page_root = tmp_path / "page_images"
    write_page_image(page_root, vision_structured, b"oversized-image")
    json_path = make_input_pair("page_blob_too_large", vision_structured, vision_report=vision_validation_report)

    result = load_input_file(
        db,
        json_path,
        persist_page_images_in_db=True,
        page_images_dir=page_root,
        max_page_image_bytes=4,
    )

    assert result.status == "loaded"
    assert db.execute("SELECT COUNT(*) FROM document_page_images").fetchone()[0] == 0


def test_same_id_reload_replaces_page_images_and_delete_cascades(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    page_root = tmp_path / "page_images"
    first = set_source_hash(vision_structured, "sha256:first-page-image")
    first_normalized = set_source_hash(vision_normalized, "sha256:first-page-image")
    second = set_source_hash(vision_structured, "sha256:second-page-image")
    second_normalized = set_source_hash(vision_normalized, "sha256:second-page-image")
    write_page_image(page_root, first, b"old-image")
    json_path = make_input_pair(
        "page_blob_reload",
        first,
        vision_report=vision_validation_report,
        normalized=first_normalized,
    )

    assert load_input_file(db, json_path, persist_page_images_in_db=True, page_images_dir=page_root).status == "loaded"
    write_page_image(page_root, second, b"new-image-version")
    json_path.write_text(json.dumps(second, indent=2, ensure_ascii=False), encoding="utf-8")
    json_path.with_name("page_blob_reload.structured.normalized.json").write_text(
        json.dumps(second_normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result = load_input_file(db, json_path, persist_page_images_in_db=True, page_images_dir=page_root)
    row = db.execute(
        "SELECT byte_size FROM document_page_images WHERE document_id = ?",
        ("page_blob_reload",),
    ).fetchone()

    assert result.status == "archived_and_loaded"
    assert db.execute("SELECT COUNT(*) FROM document_page_images WHERE document_id = ?", ("page_blob_reload",)).fetchone()[0] == 1
    assert row["byte_size"] == 17
    db.execute("DELETE FROM documents WHERE id = ?", ("page_blob_reload",))
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM document_page_images WHERE document_id = ?", ("page_blob_reload",)).fetchone()[0] == 0


def test_archived_documents_keep_linked_page_images_without_orphans(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    page_root = tmp_path / "page_images"
    first = set_source_hash(vision_structured, "sha256:first-archive")
    second = set_source_hash(vision_structured, "sha256:second-archive")
    write_page_image(page_root, first, b"archived-image")
    write_page_image(page_root, second, b"active-image")
    path_one = make_input_pair("archived_page_old", first, vision_report=vision_validation_report)
    path_two = make_input_pair("archived_page_new", second, vision_report=vision_validation_report)

    assert load_input_file(db, path_one, persist_page_images_in_db=True, page_images_dir=page_root).status == "loaded"
    result = load_input_file(db, path_two, persist_page_images_in_db=True, page_images_dir=page_root)

    rows = db.execute(
        "SELECT d.id, d.is_archived, COUNT(i.page) AS image_count "
        "FROM documents d LEFT JOIN document_page_images i ON i.document_id = d.id "
        "GROUP BY d.id, d.is_archived ORDER BY d.id"
    ).fetchall()
    assert result.status == "archived_and_loaded"
    assert [(row["id"], row["is_archived"], row["image_count"]) for row in rows] == [
        ("archived_page_new", 0, 1),
        ("archived_page_old", 1, 1),
    ]
    db.execute("DELETE FROM documents WHERE id = ?", ("archived_page_old",))
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM document_page_images WHERE document_id = ?", ("archived_page_old",)).fetchone()[0] == 0
