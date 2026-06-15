"""Runtime schema migrations for existing corpus databases."""

from __future__ import annotations

import sqlite3

from .schema_backfill import backfill_candidate_layers, backfill_evidence_anchors
from .schema_introspection import existing_table_names
from .types import CORPUS_SCHEMA_VERSION


def table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row["name"] or "") == column_name for row in rows)


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if table_has_column(conn, table_name, column_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def migrate_runtime_truth_schema(conn: sqlite3.Connection) -> None:
    existing_tables = existing_table_names(conn)
    if "installation_state" in existing_tables:
        ensure_column(conn, "installation_state", "active_snapshot_id", "TEXT")
        ensure_column(conn, "installation_state", "master_taxonomy_release_id", "TEXT")
        ensure_column(conn, "installation_state", "runtime_locale", "TEXT")
        ensure_column(conn, "installation_state", "integrity_status", "TEXT")
        conn.execute(
            "UPDATE installation_state SET schema_version = ? WHERE singleton = 1",
            (CORPUS_SCHEMA_VERSION,),
        )
    if "document_processing_state" in existing_tables:
        ensure_column(conn, "document_processing_state", "materialized_snapshot_id", "TEXT")
    if "document_promotions" in existing_tables:
        ensure_column(conn, "document_promotions", "query_role", "TEXT")
    if "document_payloads" in existing_tables:
        ensure_column(conn, "document_payloads", "raw_json", "TEXT")
        ensure_column(conn, "document_payloads", "original_file_name", "TEXT")
        ensure_column(conn, "document_payloads", "original_media_type", "TEXT")
        ensure_column(conn, "document_payloads", "original_blob", "BLOB")
    if "documents" in existing_tables:
        ensure_column(conn, "documents", "source_file_path", "TEXT")
        ensure_column(conn, "documents", "source_page", "INTEGER")
        ensure_column(conn, "documents", "source_page_count", "INTEGER")
        ensure_column(conn, "documents", "source_document_id", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "documents", "source_uri", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "documents", "source_file_id", "TEXT")
        ensure_column(conn, "documents", "source_artifact_id", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "documents", "ingest_run_id", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "documents", "page_index", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "documents", "page_label", "TEXT")
        ensure_column(conn, "documents", "materialization_order", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "documents", "page_content_hash", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "documents", "source_content_hash", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "documents", "interpreter_needs_review", "BOOLEAN DEFAULT 0")
        ensure_column(conn, "documents", "interpreter_review_reason", "TEXT")
        ensure_column(conn, "documents", "normalizer_needs_review", "BOOLEAN DEFAULT 0")
        ensure_column(conn, "documents", "normalizer_review_reason", "TEXT")
    if "document_entities" in existing_tables:
        ensure_column(conn, "document_entities", "page", "INTEGER")
        ensure_column(conn, "document_entities", "sequence", "INTEGER")
    if "evidence_atoms" in existing_tables:
        ensure_column(conn, "evidence_atoms", "anchor_kind", "TEXT")
        ensure_column(conn, "evidence_atoms", "anchor_key", "TEXT")
        backfill_evidence_anchors(conn)
    if "slot_candidates" in existing_tables:
        ensure_column(conn, "slot_candidates", "candidate_layer", "TEXT NOT NULL DEFAULT 'base'")
        ensure_column(conn, "slot_candidates", "candidate_origin", "TEXT")
        backfill_candidate_layers(conn)
