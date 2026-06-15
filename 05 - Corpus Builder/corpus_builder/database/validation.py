"""Hard validation boundaries for the corpus.db schema and query identifiers."""

from __future__ import annotations

import sqlite3

from .schema_core import CORE_INDEXES, CORE_TABLES, FTS_VIRTUAL_TABLE_SQL
from .schema_read_surface import READ_SURFACE_COLUMNS, READ_SURFACE_VIEWS
from .schema_semantics import SEMANTIC_INDEXES, SEMANTIC_TABLES
from .types import CORPUS_SCHEMA_VERSION, ddl_column_names

_SUPPORTED_SCHEMA_VERSIONS = frozenset({"5", CORPUS_SCHEMA_VERSION})

TABLE_CONTRACTS = (*CORE_TABLES, *SEMANTIC_TABLES)
INDEX_CONTRACTS = (*CORE_INDEXES, *SEMANTIC_INDEXES)
ALLOWED_TABLES = frozenset(table.name for table in TABLE_CONTRACTS) | frozenset(
    view_name for view_name, _view_sql in READ_SURFACE_VIEWS
)
ALLOWED_COLUMNS = frozenset(
    column for table in TABLE_CONTRACTS for column in ddl_column_names(table.ddl)
) | frozenset(
    column for columns in READ_SURFACE_COLUMNS.values() for column in columns
)


def ensure_compatible_existing_schema(conn: sqlite3.Connection) -> None:
    existing_tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    if not existing_tables:
        return
    if "semantic_bundle_registry" in existing_tables:
        raise ValueError(
            "Legacy corpus.db mit altem Semantic-Schema erkannt. Bitte corpus.db neu aufbauen."
        )
    if "documents" in existing_tables:
        document_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        required_columns = {
            "projection_id",
            "projection_fingerprint",
            "materialization_version",
        }
        if {"taxonomy_bundle_version", "mapping_bundle_version"} & document_columns:
            raise ValueError(
                "Legacy corpus.db mit alten Semantik-Versionen erkannt. Bitte corpus.db neu aufbauen."
            )
        if not required_columns <= document_columns:
            raise ValueError(
                "Legacy corpus.db ohne Semantic-Release-Spalten erkannt. Bitte corpus.db neu aufbauen."
            )
    if "installation_state" not in existing_tables:
        return
    state_row = conn.execute(
        "SELECT schema_version FROM installation_state WHERE singleton = 1"
    ).fetchone()
    if state_row and str(state_row["schema_version"] or "") not in _SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            "Inkompatible corpus.db erkannt. Dieser Semantic-Release-Rueckbau erfordert einen Neuaufbau."
        )


def ensure_table_name(name: str) -> str:
    if name not in ALLOWED_TABLES:
        raise ValueError(f"Unerlaubter Bezeichner: {name!r}")
    return name


def ensure_column_name(name: str) -> str:
    if name not in ALLOWED_COLUMNS:
        raise ValueError(f"Unerlaubter Bezeichner: {name!r}")
    return name
