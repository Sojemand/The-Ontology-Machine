"""Schema tests for optional page-image persistence in corpus.db."""

from __future__ import annotations

from corpus_builder.database import CORPUS_SCHEMA_VERSION, get_schema_description


def test_page_image_schema_contract_is_additive_and_frontend_compatible(db):
    columns = {
        row["name"]: row["type"]
        for row in db.execute("PRAGMA table_info(document_page_images)").fetchall()
    }
    foreign_keys = db.execute("PRAGMA foreign_key_list(document_page_images)").fetchall()
    indexes = {
        row["name"] for row in db.execute("PRAGMA index_list(document_page_images)").fetchall()
    }

    assert CORPUS_SCHEMA_VERSION == "10"
    assert columns == {
        "document_id": "TEXT",
        "page": "INTEGER",
        "content_type": "TEXT",
        "byte_size": "INTEGER",
        "image_sha256": "TEXT",
        "image_blob": "BLOB",
    }
    assert any(
        row["from"] == "document_id"
        and row["table"] == "documents"
        and row["on_delete"].upper() == "CASCADE"
        for row in foreign_keys
    )
    assert "idx_page_images_document" in indexes


def test_schema_description_mentions_document_page_images(db):
    description = get_schema_description(db)

    assert "document_page_images" in description
    assert "blob-separiert" in description


def test_semantic_read_surface_schema_exists(db):
    atom_columns = {row["name"] for row in db.execute("PRAGMA table_info(evidence_atoms)").fetchall()}
    candidate_columns = {row["name"] for row in db.execute("PRAGMA table_info(slot_candidates)").fetchall()}
    link_columns = {row["name"] for row in db.execute("PRAGMA table_info(semantic_evidence_links)").fetchall()}
    views = {
        row["name"]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'view'").fetchall()
    }

    assert {"anchor_kind", "anchor_key"} <= atom_columns
    assert {"candidate_layer", "candidate_origin"} <= candidate_columns
    assert {"subject_kind", "subject_id", "atom_id", "evidence_role"} <= link_columns
    assert {
        "vw_base_evidence_atoms",
        "vw_base_slot_candidates",
        "vw_observed_semantics",
        "vw_materialized_semantics",
    } <= views
