from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def db_update_decision(corpus_db_path: Any, release: dict[str, Any]) -> dict[str, Any]:
    db_text = str(corpus_db_path or "").strip()
    if not db_text:
        return {
            "status": "db_not_selected",
            "recommended_action": "select_current_db",
            "summary": "Select a current Corpus DB to decide update versus new materialization.",
        }
    db_path = Path(db_text).expanduser().resolve(strict=False)
    if not db_path.exists():
        return {
            "status": "new_db_required",
            "recommended_action": "materialize_new_db",
            "summary": f"Corpus DB does not exist: {db_path}",
        }
    conn = _connect_corpus_db_readonly(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return _db_update_decision_for_connection(conn, release)
    finally:
        conn.close()


def _connect_corpus_db_readonly(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True, timeout=5.0)


def _db_update_decision_for_connection(conn: sqlite3.Connection, release: dict[str, Any]) -> dict[str, Any]:
    if not _table_exists(conn, "documents"):
        return {
            "status": "update_current_db",
            "recommended_action": "update_current_db",
            "auto_refill": False,
            "summary": "DB has no initialized document table; release can seed the current DB.",
        }
    total_documents = _count_active_documents(conn)
    active_master_line = _active_master_taxonomy_release_id(conn)
    next_master_line = str(release.get("master_taxonomy_release_id") or "").strip()
    if total_documents and active_master_line and next_master_line and active_master_line != next_master_line:
        return {
            "status": "new_db_required",
            "recommended_action": "materialize_new_db",
            "summary": "Active documents belong to a different master taxonomy release line.",
            "total_documents": total_documents,
        }
    compatibility = _compatibility(conn, release)
    if compatibility["missing_projection_ids"] or compatibility["foreign_master_ids"]:
        return {
            "status": "new_db_required",
            "recommended_action": "materialize_new_db",
            "summary": "Current DB cannot be updated safely with this release.",
            **compatibility,
            "total_documents": total_documents,
        }
    needs_refill = bool(compatibility["incompatible_projection_ids"] or _stale_documents(conn))
    return {
        "status": "update_current_db",
        "recommended_action": "update_current_db_with_auto_refill" if needs_refill else "update_current_db",
        "auto_refill": needs_refill,
        "summary": "Current DB can use this release." + (" Auto refill is recommended." if needs_refill else ""),
        **compatibility,
        "total_documents": total_documents,
    }


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _count_active_documents(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "documents"):
        return 0
    return int(conn.execute("SELECT COUNT(*) FROM documents WHERE COALESCE(is_archived, 0) = 0").fetchone()[0])


def _active_master_taxonomy_release_id(conn: sqlite3.Connection) -> str:
    if not _table_exists(conn, "installation_state"):
        return ""
    row = conn.execute("SELECT master_taxonomy_release_id FROM installation_state WHERE singleton = 1 LIMIT 1").fetchone()
    return str(row["master_taxonomy_release_id"] or "").strip() if row is not None else ""


def _stale_documents(conn: sqlite3.Connection) -> int:
    if not (_table_exists(conn, "documents") and _table_exists(conn, "document_processing_state")):
        return 0
    if _table_exists(conn, "installation_state"):
        row = conn.execute("SELECT active_snapshot_id FROM installation_state WHERE singleton = 1 LIMIT 1").fetchone()
        snapshot_id = str(row["active_snapshot_id"] or "").strip() if row is not None else ""
        if snapshot_id:
            return int(
                conn.execute(
                    "SELECT COUNT(*) FROM documents d "
                    "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
                    "WHERE COALESCE(d.is_archived, 0) = 0 AND COALESCE(dps.materialized_snapshot_id, '') != ?",
                    (snapshot_id,),
                ).fetchone()[0]
            )
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM documents d "
            "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
            "WHERE COALESCE(d.is_archived, 0) = 0 AND COALESCE(dps.materialization_state, 'legacy') != 'current'"
        ).fetchone()[0]
    )


def _compatibility(conn: sqlite3.Connection, release: dict[str, Any]) -> dict[str, list[str]]:
    if not (_table_exists(conn, "documents") and _table_exists(conn, "document_payloads")):
        return {"missing_projection_ids": [], "incompatible_projection_ids": [], "foreign_master_ids": []}
    release_projection_ids = {str(value).strip() for value in release.get("projection_ids", []) or [] if str(value).strip()}
    release_master_id = str(release.get("master_taxonomy_id") or "").strip()
    missing_projection_ids: list[str] = []
    incompatible_projection_ids: list[str] = []
    foreign_master_ids: list[str] = []
    join_state = (
        "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
        if _table_exists(conn, "document_processing_state")
        else "LEFT JOIN (SELECT NULL AS document_id, NULL AS projection_id) dps ON 1 = 0 "
    )
    rows = conn.execute(
        "SELECT d.id, dps.projection_id, dp.projection_json "
        "FROM documents d "
        f"{join_state}"
        "JOIN document_payloads dp ON dp.document_id = d.id "
        "WHERE COALESCE(d.is_archived, 0) = 0"
    ).fetchall()
    for row in rows:
        document_id = str(row["id"] or "").strip()
        projection_id = str(row["projection_id"] or "").strip()
        if not projection_id:
            missing_projection_ids.append(document_id)
            continue
        if projection_id not in release_projection_ids:
            incompatible_projection_ids.append(document_id)
            continue
        projection_json = _json_object(row["projection_json"])
        input_master_id = str(projection_json.get("master_taxonomy_id") or "").strip()
        if input_master_id and release_master_id and input_master_id != release_master_id:
            foreign_master_ids.append(document_id)
    return {
        "missing_projection_ids": missing_projection_ids,
        "incompatible_projection_ids": incompatible_projection_ids,
        "foreign_master_ids": foreign_master_ids,
    }


def _json_object(raw_value: Any) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        value = json.loads(str(raw_value))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
