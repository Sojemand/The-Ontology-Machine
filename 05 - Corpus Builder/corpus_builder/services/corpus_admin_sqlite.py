"""SQLite reset mechanics for owner-local Corpus administration."""

from __future__ import annotations

import sqlite3
from typing import Any

RESET_TABLES = (
    "semantic_evidence_links",
    "candidate_evidence",
    "entity_attributes",
    "entity_relations",
    "document_promotions",
    "slot_candidates",
    "evidence_atoms",
    "document_entities",
    "document_processing_state",
    "extracted_fields",
    "extracted_rows",
    "relations",
    "tags",
    "people",
    "organizations",
    "document_page_images",
    "embedding_chunks",
    "embeddings",
    "document_payloads",
    "load_history",
    "materialization_audit",
    "materialization_runs",
    "documents",
)
PROOF_TABLES = ("documents_fts_content", *RESET_TABLES)


def release_ref(snapshot: dict[str, Any]) -> dict[str, Any]:
    release = dict(snapshot.get("release") or {})
    return {
        "active_snapshot_id": str(snapshot.get("snapshot_id") or ""),
        "release_id": str(release.get("release_id") or ""),
        "release_version": str(release.get("release_version") or ""),
        "release_fingerprint": str(release.get("fingerprint") or release.get("release_fingerprint") or ""),
        "master_taxonomy_release_id": str(snapshot.get("master_taxonomy_release_id") or release.get("master_taxonomy_release_id") or ""),
        "runtime_locale": str(snapshot.get("runtime_locale") or release.get("runtime_locale") or ""),
    }


def clear_materialized_tables(conn: sqlite3.Connection) -> int:
    cleared_fts_rows = clear_fts(conn)
    for table_name in RESET_TABLES:
        delete_table(conn, table_name)
    reset_sequences(conn, ("documents_fts_content", *RESET_TABLES))
    return cleared_fts_rows


def clear_fts(conn: sqlite3.Connection) -> int:
    if not table_exists(conn, "documents_fts_content"):
        return 0
    rows = conn.execute(
        "SELECT rowid, content_free_text, fields_text, tags_text, people_text, orgs_text "
        "FROM documents_fts_content"
    ).fetchall()
    if table_exists(conn, "documents_fts"):
        for row in rows:
            conn.execute(
                "INSERT INTO documents_fts(documents_fts, rowid, content_free_text, fields_text, tags_text, people_text, orgs_text) "
                "VALUES('delete', ?, ?, ?, ?, ?, ?)",
                (
                    row["rowid"],
                    row["content_free_text"],
                    row["fields_text"],
                    row["tags_text"],
                    row["people_text"],
                    row["orgs_text"],
                ),
            )
    conn.execute("DELETE FROM documents_fts_content")
    return len(rows)


def delete_table(conn: sqlite3.Connection, table_name: str) -> None:
    if table_exists(conn, table_name):
        conn.execute(f"DELETE FROM {table_name}")


def reset_sequences(conn: sqlite3.Connection, table_names: tuple[str, ...]) -> None:
    if not table_exists(conn, "sqlite_sequence"):
        return
    placeholders = ",".join("?" for _name in table_names)
    conn.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", table_names)


def table_counts(conn: sqlite3.Connection, table_names: tuple[str, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name in table_names:
        if table_exists(conn, table_name):
            counts[table_name] = int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
    return counts


def checkpoint_wal(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.DatabaseError:
        return


def compact_database(conn: sqlite3.Connection) -> dict[str, Any]:
    result: dict[str, Any] = {"attempted": True, "performed": False, "before": page_stats(conn)}
    try:
        conn.execute("VACUUM")
    except sqlite3.DatabaseError as exc:
        result["error"] = str(exc)
        result["after"] = page_stats(conn)
        return result
    result["performed"] = True
    result["after"] = page_stats(conn)
    return result


def page_stats(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "page_count": int(conn.execute("PRAGMA page_count").fetchone()[0]),
        "freelist_count": int(conn.execute("PRAGMA freelist_count").fetchone()[0]),
        "page_size": int(conn.execute("PRAGMA page_size").fetchone()[0]),
    }


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None
