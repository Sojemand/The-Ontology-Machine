"""Document-shaped repository helpers for corpus.db."""

from __future__ import annotations

import json
import sqlite3


def find_by_file_path(conn: sqlite3.Connection, file_path: str, archived: bool = False) -> dict | None:
    sql = "SELECT * FROM documents WHERE file_path = ?"
    if not archived:
        sql += " AND is_archived = 0"
    row = conn.execute(f"{sql} LIMIT 1", (file_path,)).fetchone()
    return dict(row) if row else None


def list_archived_documents(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT id, file_name, content_hash, archived_at, superseded_by FROM documents WHERE is_archived = 1 ORDER BY archived_at DESC"
    ).fetchall()


def clear_all_embeddings(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM embeddings")
    conn.commit()


def get_fields_dict(conn: sqlite3.Connection, doc_id: str) -> dict:
    rows = conn.execute(
        "SELECT key, value, value_type, numeric_value FROM extracted_fields WHERE document_id = ? ORDER BY id",
        (doc_id,),
    ).fetchall()
    result = {}
    for row in rows:
        value = row["value"]
        if row["value_type"] in ("number", "currency") and row["numeric_value"] is not None:
            numeric = row["numeric_value"]
            value = int(numeric) if numeric == int(numeric) and "." not in row["value"] and "," not in row["value"] else numeric
        result[row["key"]] = value
    return result


def get_rows_list(conn: sqlite3.Connection, doc_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT row_json FROM extracted_rows WHERE document_id = ? ORDER BY row_index",
        (doc_id,),
    ).fetchall()
    return [json.loads(row["row_json"]) for row in rows]


def get_relations_list(conn: sqlite3.Connection, doc_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT relation_type, target_hint, target_document_id, description, relation_origin, confidence, evidence_refs, inference_policy_version, status, created_by, created_at "
        "FROM relations WHERE document_id = ? ORDER BY id",
        (doc_id,),
    ).fetchall()
    return [
        dict(
            type=row[0],
            target_hint=row[1],
            target_document_id=row[2],
            description=row[3],
            relation_origin=row[4],
            confidence=row[5],
            evidence_refs=row[6],
            inference_policy_version=row[7],
            status=row[8],
            created_by=row[9],
            created_at=row[10],
        )
        for row in rows
    ]


def get_tags_list(conn: sqlite3.Connection, doc_id: str) -> list[str]:
    rows = conn.execute("SELECT tag FROM tags WHERE document_id = ? ORDER BY tag", (doc_id,)).fetchall()
    return [row["tag"] for row in rows]


def get_people_list(conn: sqlite3.Connection, doc_id: str) -> list[str]:
    rows = conn.execute("SELECT name FROM people WHERE document_id = ? ORDER BY name", (doc_id,)).fetchall()
    return [row["name"] for row in rows]


def get_orgs_list(conn: sqlite3.Connection, doc_id: str) -> list[str]:
    rows = conn.execute("SELECT name FROM organizations WHERE document_id = ? ORDER BY name", (doc_id,)).fetchall()
    return [row["name"] for row in rows]


__all__ = [
    "clear_all_embeddings",
    "find_by_file_path",
    "get_fields_dict",
    "get_orgs_list",
    "get_people_list",
    "get_relations_list",
    "get_rows_list",
    "get_tags_list",
    "list_archived_documents",
]
