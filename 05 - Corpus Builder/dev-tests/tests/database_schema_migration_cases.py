import sqlite3
from pathlib import Path

import pytest

from corpus_builder.database import connect_readonly, ensure_schema
from corpus_builder.loader.repository import insert_relation


def test_connect_readonly_opens_existing_database_without_wal_side_effect(tmp_path: Path) -> None:
    db_path = tmp_path / "folder with spaces" / "readonly corpus.db"
    db_path.parent.mkdir()
    writer = sqlite3.connect(db_path)
    try:
        writer.execute("CREATE TABLE sample (id TEXT PRIMARY KEY)")
        writer.execute("INSERT INTO sample (id) VALUES ('row_1')")
        writer.commit()
    finally:
        writer.close()

    conn = connect_readonly(str(db_path))
    try:
        assert conn.execute("SELECT COUNT(*) FROM sample").fetchone()[0] == 1
    finally:
        conn.close()

    assert not db_path.with_name(f"{db_path.name}-wal").exists()


def test_ensure_schema_rejects_legacy_bundle_schema():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        CREATE TABLE documents (
            id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            file_size_bytes INTEGER,
            document_type TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            language TEXT,
            is_scan BOOLEAN DEFAULT 0,
            has_handwriting BOOLEAN DEFAULT 0,
            page_count INTEGER DEFAULT 1,
            company TEXT,
            document_date TEXT,
            document_title TEXT,
            description TEXT,
            monetary_value REAL,
            total_hours REAL,
            tax_amount REAL,
            net_amount REAL,
            tax_rate REAL,
            reference_number TEXT,
            due_date TEXT,
            counterparty TEXT,
            opening_balance REAL,
            closing_balance REAL,
            date_range_from TEXT,
            date_range_to TEXT,
            model TEXT NOT NULL,
            model_confidence REAL NOT NULL,
            needs_review BOOLEAN DEFAULT 0,
            vision_used BOOLEAN DEFAULT 0,
            validator_status TEXT NOT NULL,
            validator_issues_count INTEGER DEFAULT 0,
            content_structure TEXT,
            content_fields_json TEXT,
            content_rows_json TEXT,
            content_free_text TEXT,
            loaded_at TEXT NOT NULL,
            updated_at TEXT,
            is_archived BOOLEAN DEFAULT 0,
            archived_at TEXT,
            superseded_by TEXT
        )
        """
    )

    with pytest.raises(ValueError, match="neu aufbauen|Neuaufbau"):
        ensure_schema(conn)
    conn.close()


def test_ensure_schema_fails_fast_when_fts_cannot_be_created(monkeypatch):
    from corpus_builder.database import workflow as database_workflow

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    monkeypatch.setattr(
        database_workflow,
        "FTS_VIRTUAL_TABLE_SQL",
        "CREATE VIRTUAL TABLE documents_fts USING missing_fts_engine(content)",
    )

    with pytest.raises(RuntimeError, match="FTS5"):
        database_workflow.ensure_schema(conn)
    conn.close()


def test_ensure_schema_backfills_source_identity_columns(db):
    db.execute(
        "INSERT INTO documents (id, file_name, file_path, content_hash, document_type, category, language, model, model_confidence, validator_status, loaded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (
            "source_doc",
            "mail_case.msg",
            "mail_case.msg::page=002-of-005",
            "sha256:source-doc",
            "general_letter",
            "business",
            "de",
            "gpt-test",
            0.9,
            "pass",
        ),
    )

    ensure_schema(db)

    row = db.execute(
        "SELECT source_file_path, source_page, source_page_count, source_document_id, source_uri, "
        "source_artifact_id, ingest_run_id, page_index, page_label, materialization_order, "
        "page_content_hash, source_content_hash FROM documents WHERE id = ?",
        ("source_doc",),
    ).fetchone()
    assert dict(row) == {
        "source_file_path": "mail_case.msg",
        "source_page": 2,
        "source_page_count": 5,
        "source_document_id": "mail_case.msg",
        "source_uri": "mail_case.msg",
        "source_artifact_id": "mail_case.msg",
        "ingest_run_id": "default",
        "page_index": 1,
        "page_label": "2",
        "materialization_order": 1,
        "page_content_hash": "sha256:source-doc",
        "source_content_hash": "sha256:source-doc",
    }


def test_relations_schema_supports_observed_and_inferred_metadata_defaults(db):
    relation_columns = {row["name"] for row in db.execute("PRAGMA table_info(relations)").fetchall()}
    entity_relation_columns = {row["name"] for row in db.execute("PRAGMA table_info(entity_relations)").fetchall()}
    entity_columns = {row["name"] for row in db.execute("PRAGMA table_info(document_entities)").fetchall()}

    expected = {
        "relation_origin",
        "confidence",
        "evidence_refs",
        "inference_policy_version",
        "status",
        "created_by",
        "created_at",
    }
    assert expected <= relation_columns
    assert expected <= entity_relation_columns
    assert {"page", "sequence"} <= entity_columns

    db.execute(
        "INSERT INTO documents (id, file_name, file_path, content_hash, document_type, category, language, model, model_confidence, validator_status, loaded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (
            "relation_doc",
            "relation_doc.pdf",
            "C:/tmp/relation_doc.pdf",
            "sha256:relation-doc",
            "general_letter",
            "business",
            "de",
            "gpt-test",
            0.9,
            "pass",
        ),
    )
    insert_relation(
        db,
        "relation_doc",
        {"type": "normalized_from", "target_hint": "relation_doc.structured.json", "description": "generated during load"},
    )

    row = db.execute(
        "SELECT relation_origin, confidence, evidence_refs, inference_policy_version, status, created_by, created_at "
        "FROM relations WHERE document_id = ?",
        ("relation_doc",),
    ).fetchone()
    assert row["relation_origin"] == "observed"
    assert row["confidence"] is None
    assert row["evidence_refs"] == "relations"
    assert row["inference_policy_version"] is None
    assert row["status"] == "observed"
    assert row["created_by"] == "corpus_builder"
    assert row["created_at"]
