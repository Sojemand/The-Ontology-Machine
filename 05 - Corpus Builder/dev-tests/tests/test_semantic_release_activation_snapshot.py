from __future__ import annotations

import json

import pytest

from corpus_builder.database import connect, ensure_schema
from corpus_builder.semantic_release import load_release_from_path
from corpus_builder.services import activation_preflight, apply_semantic_release, load_semantic_release, read_active_semantic_release
from .semantic_release_surface_support import _make_context

def test_read_active_semantic_release_rejects_initialized_db_without_snapshot(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    db_path = context.output_dir / "test.corpus.db"
    conn = connect(str(db_path))
    try:
        ensure_schema(conn)
    finally:
        conn.close()

    with pytest.raises(ValueError, match="active_snapshot"):
        read_active_semantic_release(context, corpus_db_path=db_path)

def test_activation_preflight_allows_merge_target_documents_before_first_snapshot(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    db_path = context.output_dir / "merged.corpus.db"
    release_path = context.config_dir / "semantic_release.default.json"
    release = load_release_from_path(release_path)
    projection = release["projections"][0]
    loaded_at = "2026-05-28T19:17:53Z"
    conn = connect(str(db_path))
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO documents "
            "(id, file_name, file_path, content_hash, document_type, category, model, model_confidence, "
            "validator_status, loaded_at, projection_id, projection_fingerprint, content_free_text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "doc_merge_001",
                "merged.txt",
                "merged.txt",
                "sha256:merged-doc",
                "communication",
                "business",
                "test-model",
                1.0,
                "ok",
                loaded_at,
                projection["projection_id"],
                projection["projection_fingerprint"],
                "merged content",
            ),
        )
        conn.execute(
            "INSERT INTO document_payloads "
            "(document_id, structured_json, projection_json, release_fingerprint, free_text, loaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                "doc_merge_001",
                "{}",
                json.dumps({"master_taxonomy_id": "source.master.line", "projection_id": projection["projection_id"]}),
                "sha256:source-release",
                "merged content",
                loaded_at,
            ),
        )
        conn.execute(
            "INSERT INTO document_processing_state "
            "(document_id, projection_id, projection_fingerprint, materialization_state, source_mode, last_materialized_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                "doc_merge_001",
                projection["projection_id"],
                projection["projection_fingerprint"],
                "current",
                "structured",
                loaded_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    loaded = load_semantic_release(
        context,
        release_path=release_path,
        corpus_db_path=db_path,
        write_global_mirrors=False,
    )
    preflight = activation_preflight(context, release_path=release_path, corpus_db_path=db_path)
    applied = apply_semantic_release(context, release_path=release_path, corpus_db_path=db_path, write_global_mirrors=False)

    assert loaded["status"]["runtime_truth_source"] == "uninitialized"
    assert loaded["status"]["total_documents"] == 1
    assert preflight["initialization_required"] is True
    assert preflight["db_changes"]["total_documents"] == 1
    assert preflight["requires_confirmation"] is False
    assert applied["active_snapshot_id"]
    assert applied["initial_payload_headers_aligned_count"] == 1
    assert read_active_semantic_release(context, corpus_db_path=db_path)["active_snapshot"]["snapshot_id"] == applied["active_snapshot_id"]
    conn = connect(str(db_path))
    try:
        payload_row = conn.execute("SELECT release_fingerprint, projection_json FROM document_payloads WHERE document_id = ?", ("doc_merge_001",)).fetchone()
        projection_json = json.loads(payload_row["projection_json"])
        assert payload_row["release_fingerprint"] == release["fingerprint"]
        assert projection_json["master_taxonomy_id"] == release["master_taxonomy_id"]
        assert projection_json["projection_id"] == projection["projection_id"]
    finally:
        conn.close()

def test_activation_preflight_still_blocks_foreign_master_after_snapshot_is_active(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    db_path = context.output_dir / "active.corpus.db"
    release_path = context.config_dir / "semantic_release.default.json"
    release = load_release_from_path(release_path)
    projection = release["projections"][0]
    loaded_at = "2026-05-28T19:29:00Z"
    conn = connect(str(db_path))
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO documents "
            "(id, file_name, file_path, content_hash, document_type, category, model, model_confidence, "
            "validator_status, loaded_at, projection_id, projection_fingerprint) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "doc_active_001",
                "active.txt",
                "active.txt",
                "sha256:active-doc",
                "communication",
                "business",
                "test-model",
                1.0,
                "ok",
                loaded_at,
                projection["projection_id"],
                projection["projection_fingerprint"],
            ),
        )
        conn.execute(
            "INSERT INTO document_payloads "
            "(document_id, structured_json, projection_json, release_fingerprint, loaded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "doc_active_001",
                "{}",
                json.dumps({"master_taxonomy_id": release["master_taxonomy_id"], "projection_id": projection["projection_id"]}),
                release["fingerprint"],
                loaded_at,
            ),
        )
        conn.execute(
            "INSERT INTO document_processing_state "
            "(document_id, projection_id, projection_fingerprint, materialization_state, source_mode, last_materialized_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                "doc_active_001",
                projection["projection_id"],
                projection["projection_fingerprint"],
                "current",
                "structured",
                loaded_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    apply_semantic_release(context, release_path=release_path, corpus_db_path=db_path, write_global_mirrors=False)
    conn = connect(str(db_path))
    try:
        conn.execute(
            "UPDATE document_payloads SET projection_json = ? WHERE document_id = ?",
            (json.dumps({"master_taxonomy_id": "foreign.master.line", "projection_id": projection["projection_id"]}), "doc_active_001"),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="anderer Master-Linie|anderer Master"):
        activation_preflight(context, release_path=release_path, corpus_db_path=db_path)
