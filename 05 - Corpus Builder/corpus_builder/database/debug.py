"""Debug helpers for live corpus.db schema introspection."""

from __future__ import annotations

import sqlite3

from .validation import TABLE_CONTRACTS


def _existing_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row["name"] for row in rows}


def _foreign_key_lines(conn: sqlite3.Connection, table_name: str) -> list[str]:
    lines: list[str] = []
    for row in conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall():
        lines.append(f"- {table_name}.{row['from']} -> {row['table']}.{row['to']}")
    return lines


def get_schema_description(conn: sqlite3.Connection) -> str:
    """Gibt eine menschenlesbare Beschreibung des aktuellen Schemas zurueck."""
    lines = ["# corpus.db Schema", "", "## Tabellen und Spalten", ""]
    existing_tables = _existing_table_names(conn)

    for table in TABLE_CONTRACTS:
        if table.name not in existing_tables or table.name == "documents_fts_content":
            continue
        lines.append(f"### {table.name}")
        for column in conn.execute(f"PRAGMA table_info({table.name})").fetchall():
            name = column["name"]
            column_type = column["type"] or "TEXT"
            pk = " (PK)" if column["pk"] else ""
            not_null = " NOT NULL" if column["notnull"] else ""
            default = f" DEFAULT {column['dflt_value']}" if column["dflt_value"] is not None else ""
            lines.append(f"  - {name}: {column_type}{pk}{not_null}{default}")
        lines.append("")

    relation_lines = [
        line
        for table in TABLE_CONTRACTS
        if table.name in existing_tables
        for line in _foreign_key_lines(conn, table.name)
    ]
    lines.extend(["## Beziehungen", *relation_lines, "", "## Hinweise"])
    lines.extend(
        f"- {table.debug_hint}" for table in TABLE_CONTRACTS if table.name in existing_tables
    )
    return "\n".join(lines)
