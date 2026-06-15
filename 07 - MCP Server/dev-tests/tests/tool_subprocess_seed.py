from __future__ import annotations

import json
import sqlite3


def _seed_document(db_path: str, document_id: str, *, free_text: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        state = _active_release_state(conn)
        loaded_at = "2026-04-24T00:00:00Z"
        projection_json = {
            "projection_id": state["projection_id"],
            "projection_fingerprint": state["projection_fingerprint"],
            "master_taxonomy_id": state["master_taxonomy_id"],
            "master_taxonomy_version": state["master_taxonomy_version"],
        }
        structured_payload = {
            "schema_version": "l2.integration.seed.v1",
            "document_id": document_id,
            "context": {
                "document_title": f"L2 {document_id}",
                "document_date": "2026-04-24",
                "taxonomy_profile_id": state["projection_id"],
            },
            "content": {"free_text": free_text, "fields": {"amount_due": "42.00", "company": "L2 Company"}},
            "projection": projection_json,
        }
        _insert_document(conn, document_id, free_text, state, loaded_at)
        _insert_payload(conn, document_id, structured_payload, projection_json, state["release_fingerprint"], free_text, loaded_at)
        _insert_processing_state(conn, document_id, state, loaded_at)
        _insert_search_rows(conn, document_id, free_text)
        conn.commit()
    finally:
        conn.close()


def _insert_document(conn: sqlite3.Connection, document_id: str, free_text: str, state: dict[str, str], loaded_at: str) -> None:
    fields_json = json.dumps({"amount_due": "42.00", "company": "L2 Company"}, ensure_ascii=False)
    conn.execute(
        "INSERT OR REPLACE INTO documents "
        "(id, file_name, file_path, source_file_path, source_page, source_page_count, content_hash, "
        "file_size_bytes, document_type, document_type_confidence, category, subcategory, language, is_scan, "
        "has_handwriting, page_count, model, model_confidence, needs_review, interpreter_needs_review, "
        "interpreter_review_reason, normalizer_needs_review, normalizer_review_reason, vision_used, "
        "materialization_version, projection_id, projection_fingerprint, validator_status, "
        "validator_issues_count, content_structure, content_fields_json, content_rows_json, content_free_text, loaded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            document_id, f"{document_id}.pdf", f"/tmp/{document_id}.pdf", f"/tmp/{document_id}.pdf",
            None, None, f"hash-{document_id}", 0, "invoice", 0.99, "finance", None, "de", 0, 0, 1,
            "fixture", 0.99, 0, 0, None, 0, None, 0, state["materialization_version"],
            state["projection_id"], state["projection_fingerprint"], "passed", 0, "free_text",
            fields_json, json.dumps([], ensure_ascii=False), free_text, loaded_at,
        ),
    )


def _insert_payload(
    conn: sqlite3.Connection,
    document_id: str,
    structured_payload: dict[str, object],
    projection_json: dict[str, str],
    release_fingerprint: str,
    free_text: str,
    loaded_at: str,
) -> None:
    encoded = json.dumps(structured_payload, ensure_ascii=False)
    conn.execute(
        "INSERT OR REPLACE INTO document_payloads "
        "(document_id, schema_version, structured_json, normalized_json, projection_json, release_fingerprint, free_text, loaded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            document_id, "l2.integration.seed.v1", encoded, encoded,
            json.dumps(projection_json, ensure_ascii=False), release_fingerprint, free_text, loaded_at,
        ),
    )


def _insert_processing_state(conn: sqlite3.Connection, document_id: str, state: dict[str, str], loaded_at: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO document_processing_state "
        "(document_id, schema_version, materialization_version, materialized_snapshot_id, projection_id, "
        "projection_fingerprint, materialization_state, source_mode, last_materialized_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            document_id, "document_processing_state.v1", state["materialization_version"],
            state["active_snapshot_id"], state["projection_id"], state["projection_fingerprint"],
            "current", "structured", loaded_at,
        ),
    )


def _insert_search_rows(conn: sqlite3.Connection, document_id: str, free_text: str) -> None:
    conn.execute(
        "INSERT INTO extracted_fields "
        "(document_id, key, value, value_type, numeric_value, confidence, source, normalized_value, compact_value) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (document_id, "amount_due", "42.00", "number", 42.0, "high", "content.fields.amount_due", "42.00", "4200"),
    )
    conn.execute("INSERT OR REPLACE INTO tags (document_id, tag, normalized_tag, compact_tag) VALUES (?, ?, ?, ?)", (document_id, "l2", "l2", "l2"))
    conn.execute(
        "INSERT OR REPLACE INTO organizations (document_id, name, normalized_name, compact_name) VALUES (?, ?, ?, ?)",
        (document_id, "L2 Company", "l2 company", "l2company"),
    )
    rowid = int(conn.execute(
        "INSERT INTO documents_fts_content (document_id, content_free_text, fields_text, tags_text, people_text, orgs_text) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (document_id, free_text, "amount_due 42.00", "l2", "", "L2 Company"),
    ).lastrowid)
    conn.execute(
        "INSERT INTO documents_fts (rowid, content_free_text, fields_text, tags_text, people_text, orgs_text) VALUES (?, ?, ?, ?, ?, ?)",
        (rowid, free_text, "amount_due 42.00", "l2", "", "L2 Company"),
    )


def _active_release_state(conn: sqlite3.Connection) -> dict[str, str]:
    installation = conn.execute(
        "SELECT active_snapshot_id, active_release_fingerprint, master_taxonomy_id, master_taxonomy_version, "
        "materialization_version FROM installation_state WHERE singleton = 1 LIMIT 1"
    ).fetchone()
    active_snapshot_id = str(installation["active_snapshot_id"] or "") if installation else ""
    snapshot = conn.execute("SELECT release_json FROM semantic_snapshots WHERE snapshot_id = ? LIMIT 1", (active_snapshot_id,)).fetchone()
    release = json.loads(snapshot["release_json"]) if snapshot and snapshot["release_json"] else {}
    projection = _default_projection(release)
    return {
        "active_snapshot_id": active_snapshot_id,
        "release_fingerprint": str(_row_value(installation, "active_release_fingerprint") or release.get("fingerprint") or ""),
        "materialization_version": str(_row_value(installation, "materialization_version") or release.get("materialization_version") or "1"),
        "master_taxonomy_id": str(_row_value(installation, "master_taxonomy_id") or release.get("master_taxonomy_id") or ""),
        "master_taxonomy_version": str(_row_value(installation, "master_taxonomy_version") or release.get("master_taxonomy_version") or ""),
        "projection_id": str(projection.get("projection_id") or "finance.default.v1"),
        "projection_fingerprint": str(projection.get("projection_fingerprint") or projection.get("fingerprint") or ""),
    }


def _default_projection(release: dict[str, object]) -> dict[str, object]:
    projections = release.get("projections") if isinstance(release.get("projections"), list) else []
    return next(
        (item for item in projections if isinstance(item, dict) and str(item.get("projection_id") or "") == "finance.default.v1"),
        projections[0] if projections else {},
    )


def _row_value(row: sqlite3.Row | None, key: str) -> object:
    if row is None or key not in row.keys():
        return None
    return row[key]
