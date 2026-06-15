"""Repository stage for corpus stats DB reads."""

from __future__ import annotations

import sqlite3

from ..database import avg, count, group_count, top_n
from .types import CorpusDateRange

ACTIVE_DOCUMENTS_WHERE = "is_archived = 0"
ARCHIVED_DOCUMENTS_WHERE = "is_archived = 1"


def fetch_overview(conn: sqlite3.Connection) -> dict[str, int | bool]:
    embeddings_count = count(conn, "embeddings")
    if _table_exists(conn, "embedding_chunks"):
        embeddings_count += count(conn, "embedding_chunks")
    return {
        "total_documents": count(conn, "documents", ACTIVE_DOCUMENTS_WHERE),
        "total_archived": count(conn, "documents", ARCHIVED_DOCUMENTS_WHERE),
        "total_fields": count(conn, "extracted_fields"),
        "total_relations": count(conn, "relations"),
        "total_entities": count(conn, "document_entities"),
        "stale_documents": conn.execute(
            "SELECT COUNT(*) "
            "FROM documents d "
            "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
            "WHERE d.is_archived = 0 AND COALESCE(dps.materialization_state, 'legacy') != 'current'"
        ).fetchone()[0],
        "has_embeddings": embeddings_count > 0,
        "embeddings_count": embeddings_count,
    }


def fetch_document_groups(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    return {
        "by_document_type": group_count(conn, "documents", "document_type", ACTIVE_DOCUMENTS_WHERE),
        "by_category": group_count(conn, "documents", "category", ACTIVE_DOCUMENTS_WHERE),
        "by_language": group_count(conn, "documents", "language", ACTIVE_DOCUMENTS_WHERE),
        "by_validator_status": group_count(conn, "documents", "validator_status", ACTIVE_DOCUMENTS_WHERE),
        "by_promotion_slot": fetch_promotion_slot_counts(conn),
        "by_projection": {
            str(row["projection_id"]): int(row["count"] or 0)
            for row in conn.execute(
                "SELECT dps.projection_id AS projection_id, COUNT(*) AS count "
                "FROM documents d "
                "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
                "WHERE d.is_archived = 0 AND COALESCE(dps.projection_id, '') != '' "
                "GROUP BY dps.projection_id"
            ).fetchall()
        },
        "by_materialization_state": {
            str(row["materialization_state"] or "legacy"): int(row["count"] or 0)
            for row in conn.execute(
                "SELECT COALESCE(dps.materialization_state, 'legacy') AS materialization_state, COUNT(*) AS count "
                "FROM documents d "
                "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
                "WHERE d.is_archived = 0 "
                "GROUP BY COALESCE(dps.materialization_state, 'legacy')"
            ).fetchall()
        },
    }


def fetch_entity_type_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT de.entity_type, COUNT(*) AS cnt "
        "FROM document_entities de "
        "JOIN documents d ON de.document_id = d.id "
        "WHERE d.is_archived = 0 "
        "GROUP BY de.entity_type ORDER BY cnt DESC"
    )
    return {str(row[0] or "null"): row[1] for row in rows}


def fetch_top_rankings(conn: sqlite3.Connection) -> dict[str, list[tuple[str, int]]]:
    return {
        "top_tags": top_n(conn, "tags", "tag", 20),
        "top_people": top_n(conn, "people", "name", 20),
        "top_organizations": top_n(conn, "organizations", "name", 20),
        "top_field_keys": top_n(conn, "extracted_fields", "key", 20),
        "top_promotion_values": fetch_top_promotion_values(conn),
    }


def fetch_numeric_stats(conn: sqlite3.Connection, *, total_documents: int) -> dict[str, object]:
    return {
        "avg_confidence": avg(conn, "documents", "model_confidence", ACTIVE_DOCUMENTS_WHERE),
        "avg_fields_per_doc": fetch_avg_fields_per_doc(conn, total_documents=total_documents),
        "date_range": fetch_date_range(conn),
        "promotion_numeric_totals": fetch_promotion_numeric_totals(conn),
    }


def fetch_avg_fields_per_doc(
    conn: sqlite3.Connection,
    *,
    total_documents: int,
) -> float | None:
    if total_documents <= 0:
        return None
    total_fields = conn.execute(
        "SELECT COUNT(*) FROM extracted_fields ef "
        "JOIN documents d ON ef.document_id = d.id "
        "WHERE d.is_archived = 0"
    ).fetchone()[0]
    return round(total_fields / total_documents, 1)


def fetch_date_range(conn: sqlite3.Connection) -> CorpusDateRange:
    if not _table_exists(conn, "document_promotions"):
        return {"earliest": None, "latest": None}
    row = conn.execute(
        "SELECT MIN(p.date_value) AS earliest, MAX(p.date_value) AS latest "
        "FROM document_promotions p "
        "JOIN documents d ON d.id = p.document_id "
        "WHERE d.is_archived = 0 AND p.is_current = 1 AND p.date_value IS NOT NULL"
    ).fetchone()
    return {
        "earliest": row["earliest"] if row else None,
        "latest": row["latest"] if row else None,
    }


def fetch_promotion_slot_counts(conn: sqlite3.Connection) -> dict[str, int]:
    if not _table_exists(conn, "document_promotions"):
        return {}
    rows = conn.execute(
        "SELECT p.slot, COUNT(DISTINCT p.document_id) AS cnt "
        "FROM document_promotions p "
        "JOIN documents d ON d.id = p.document_id "
        "WHERE d.is_archived = 0 AND p.is_current = 1 "
        "GROUP BY p.slot ORDER BY cnt DESC, p.slot"
    ).fetchall()
    return {str(row["slot"] or "null"): int(row["cnt"] or 0) for row in rows}


def fetch_top_promotion_values(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    if not _table_exists(conn, "document_promotions"):
        return []
    rows = conn.execute(
        "SELECT p.slot, p.display_value, COUNT(*) AS cnt "
        "FROM document_promotions p "
        "JOIN documents d ON d.id = p.document_id "
        "WHERE d.is_archived = 0 AND p.is_current = 1 AND COALESCE(p.display_value, '') != '' "
        "GROUP BY p.slot, p.display_value ORDER BY cnt DESC, p.slot, p.display_value LIMIT 20"
    ).fetchall()
    return [(f"{row['slot']}: {row['display_value']}", int(row["cnt"] or 0)) for row in rows]


def fetch_promotion_numeric_totals(conn: sqlite3.Connection) -> dict[str, float]:
    if not _table_exists(conn, "document_promotions"):
        return {}
    rows = conn.execute(
        "SELECT p.slot, SUM(p.numeric_value) AS total "
        "FROM document_promotions p "
        "JOIN documents d ON d.id = p.document_id "
        "WHERE d.is_archived = 0 AND p.is_current = 1 AND p.numeric_value IS NOT NULL "
        "GROUP BY p.slot ORDER BY p.slot"
    ).fetchall()
    return {str(row["slot"]): float(row["total"]) for row in rows if row["total"] is not None}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None
