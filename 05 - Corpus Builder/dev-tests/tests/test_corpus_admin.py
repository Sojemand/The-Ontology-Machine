from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from corpus_builder.context import ModuleContext
from corpus_builder.database import connect
from corpus_builder.services import apply_semantic_release, read_active_semantic_release
from corpus_builder.services.corpus_admin import reset_active_corpus_db

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _context(tmp_path: Path) -> ModuleContext:
    (tmp_path / "config").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "output").mkdir()
    release_text = (PROJECT_ROOT / "config" / "semantic_release.default.json").read_text(encoding="utf-8")
    (tmp_path / "config" / "semantic_release.default.json").write_text(release_text, encoding="utf-8")
    (tmp_path / "config" / "corpus_config.json").write_text(
        json.dumps(
            {
                "database": {"corpus_db": str(tmp_path / "output" / "active.db")},
                "semantic": {
                    "published_release_path": str(tmp_path / "config" / "semantic_release.default.json"),
                    "active_release_path": str(tmp_path / "state" / "semantic_release.active.json"),
                    "release_report_path": str(tmp_path / "state" / "semantic_release_report.json"),
                },
            }
        ),
        encoding="utf-8",
    )
    return ModuleContext(tmp_path)


def _confirmation(path: Path, db_path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "artifact_version": "reset_active_corpus_db_confirmation_v1",
                "requested_action": "reset_active_corpus_db",
                "confirmed": True,
                "corpus_db_path": str(db_path.resolve()),
                "reason": "test reset",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_reset_active_corpus_db_requires_matching_confirmation(tmp_path: Path) -> None:
    context = _context(tmp_path)
    db_path = tmp_path / "output" / "active.db"
    sqlite3.connect(db_path).close()
    confirmation = _confirmation(tmp_path / "confirm.json", tmp_path / "output" / "other.db")

    with pytest.raises(ValueError, match="andere Corpus DB"):
        reset_active_corpus_db(context, confirmation_artifact_path=confirmation)


def test_reset_active_corpus_db_clears_content_and_preserves_active_release(tmp_path: Path) -> None:
    context = _context(tmp_path)
    db_path = tmp_path / "output" / "active.db"
    release_path = tmp_path / "config" / "semantic_release.default.json"
    apply_semantic_release(context, release_path=release_path, corpus_db_path=db_path, write_global_mirrors=False)
    active_before = read_active_semantic_release(context, corpus_db_path=db_path)
    _insert_materialized_document(db_path)
    confirmation = _confirmation(tmp_path / "confirm.json", db_path)

    result = reset_active_corpus_db(context, confirmation_artifact_path=confirmation)

    assert result["status"] == "ok"
    assert result["corpus_db_path"] == str(db_path.resolve())
    assert result["semantic_release_preserved"] is True
    assert result["empty_state_proven"] is True
    assert result["physical_compaction"]["attempted"] is True
    assert result["physical_compaction_performed"] is True
    assert result["wal_sidecar_cleanup"]["attempted"] is True
    assert not Path(str(db_path.resolve()) + "-wal").exists()
    assert not Path(str(db_path.resolve()) + "-shm").exists()
    active_after = read_active_semantic_release(context, corpus_db_path=db_path)
    assert active_after["fingerprint"] == active_before["fingerprint"]
    assert active_after["active_snapshot"]["snapshot_id"] == active_before["active_snapshot"]["snapshot_id"]
    conn = connect(str(db_path))
    try:
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM document_promotions").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM embedding_chunks").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM documents_fts_content").fetchone()[0] == 0
        assert conn.execute("SELECT active_release_fingerprint FROM installation_state WHERE singleton = 1").fetchone()[0] == active_before["fingerprint"]
        assert conn.execute("SELECT COUNT(*) FROM semantic_snapshots").fetchone()[0] == 1
    finally:
        conn.close()


def _insert_materialized_document(db_path: Path) -> None:
    conn = connect(str(db_path))
    try:
        loaded_at = "2026-05-30T12:00:00Z"
        conn.execute(
            "INSERT INTO documents "
            "(id, file_name, file_path, content_hash, document_type, category, model, model_confidence, validator_status, loaded_at, content_free_text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("doc_001", "source.txt", "source.txt", "sha256:doc001", "text", "test", "test-model", 1.0, "ok", loaded_at, "hello reset"),
        )
        conn.execute(
            "INSERT INTO document_payloads (document_id, structured_json, normalized_json, loaded_at) VALUES (?, ?, ?, ?)",
            ("doc_001", "{}", "{}", loaded_at),
        )
        conn.execute(
            "INSERT INTO extracted_fields (document_id, key, value) VALUES (?, ?, ?)",
            ("doc_001", "title", "Hello Reset"),
        )
        conn.execute(
            "INSERT INTO evidence_atoms (document_id, atom_type, json_path, text_value) VALUES (?, ?, ?, ?)",
            ("doc_001", "field", "content.fields.title", "Hello Reset"),
        )
        candidate_id = conn.execute(
            "INSERT INTO slot_candidates (document_id, slot, display_value, strategy) VALUES (?, ?, ?, ?)",
            ("doc_001", "title", "Hello Reset", "test"),
        ).lastrowid
        conn.execute(
            "INSERT INTO document_promotions (document_id, slot, value_type, display_value, ordinal, candidate_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("doc_001", "title", "string", "Hello Reset", 0, candidate_id, loaded_at),
        )
        conn.execute(
            "INSERT INTO embeddings (document_id, embedding_text, vector, model, dimensions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc_001", "Hello Reset", b"1234", "test-embedding", 4, loaded_at),
        )
        conn.execute(
            "INSERT INTO embedding_chunks (chunk_id, document_id, chunk_index, chunk_type, source_kind, source_refs_json, chunk_text, vector, model, dimensions, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("chunk_001", "doc_001", 0, "document", "document", "[]", "Hello Reset", b"1234", "test-embedding", 4, loaded_at),
        )
        rowid = conn.execute(
            "INSERT INTO documents_fts_content (document_id, content_free_text, fields_text, tags_text, people_text, orgs_text) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc_001", "hello reset", "title hello reset", "", "", ""),
        ).lastrowid
        conn.execute(
            "INSERT INTO documents_fts(rowid, content_free_text, fields_text, tags_text, people_text, orgs_text) VALUES (?, ?, ?, ?, ?, ?)",
            (rowid, "hello reset", "title hello reset", "", "", ""),
        )
        conn.execute(
            "INSERT INTO materialization_runs (action, started_at) VALUES (?, ?)",
            ("test_materialization", loaded_at),
        )
        conn.commit()
    finally:
        conn.close()
