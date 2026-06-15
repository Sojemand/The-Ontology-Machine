"""Schema workflow for corpus.db creation and compatibility checks."""

from __future__ import annotations

import sqlite3

from .schema_introspection import existing_table_names
from .schema_migrations import migrate_runtime_truth_schema
from .schema_read_surface import READ_SURFACE_VIEWS
from .schema_source_identity_backfill import backfill_source_identity
from .types import CORPUS_SCHEMA_VERSION, DEPRECATED_TABLES
from .validation import (
    FTS_VIRTUAL_TABLE_SQL,
    INDEX_CONTRACTS,
    TABLE_CONTRACTS,
    ensure_compatible_existing_schema,
)

_READ_REQUIRED_TABLES = frozenset(table.name for table in TABLE_CONTRACTS)
_READ_OPTIONAL_TABLES = frozenset({"semantic_snapshots", "embedding_chunks"})


def _schema_sql() -> str:
    return "\n\n".join(table.ddl for table in TABLE_CONTRACTS)


def _index_sql() -> str:
    return "\n".join(index.sql for index in INDEX_CONTRACTS)


def _view_sql() -> str:
    return "\n\n".join(view_sql for _view_name, view_sql in READ_SURFACE_VIEWS)


def _drop_read_surface_views(conn: sqlite3.Connection) -> None:
    for view_name, _view_sql_text in READ_SURFACE_VIEWS:
        conn.execute(f"DROP VIEW IF EXISTS {view_name}")


def _ensure_read_surface_views(conn: sqlite3.Connection) -> None:
    _drop_read_surface_views(conn)
    conn.executescript(_view_sql())


def _ensure_fts_table(conn: sqlite3.Connection) -> None:
    try:
        conn.execute(FTS_VIRTUAL_TABLE_SQL)
    except sqlite3.OperationalError as exc:
        if "already exists" in str(exc).lower():
            return
        raise RuntimeError(
            "SQLite FTS5 ist nicht verfuegbar; corpus.db kann den Suchvertrag nicht initialisieren."
        ) from exc


def _seed_installation_state(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO installation_state "
        "(singleton, schema_version, active_snapshot_id, active_release_id, active_release_version, active_release_fingerprint, "
        "master_taxonomy_id, master_taxonomy_version, master_taxonomy_release_id, runtime_locale, materialization_version, updated_at) "
        "VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, CURRENT_TIMESTAMP)",
        (1, CORPUS_SCHEMA_VERSION),
    )


def has_initialized_schema(conn: sqlite3.Connection, *, require_fts: bool = False) -> bool:
    """Validate compatibility and report whether the full read schema already exists."""
    ensure_compatible_existing_schema(conn)
    required_tables = set(_READ_REQUIRED_TABLES - _READ_OPTIONAL_TABLES)
    if require_fts:
        required_tables.add("documents_fts")
    return required_tables <= existing_table_names(conn)


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Erstellt das aktuelle Schema oder blockt alte Corpora als Reset-Fall."""
    ensure_compatible_existing_schema(conn)
    for table_name in DEPRECATED_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.executescript(_schema_sql())
    migrate_runtime_truth_schema(conn)
    conn.executescript(_index_sql())
    _ensure_fts_table(conn)
    _ensure_read_surface_views(conn)
    backfill_source_identity(conn)
    _seed_installation_state(conn)
    conn.commit()
