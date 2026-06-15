from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from semantic_control_kernel.validation.ontology_validation_contract import (
    JSON_COLUMNS,
    REQUIRED_ONTOLOGY_TABLES,
    SEMANTIC_REF_TARGETS,
)


def _connect_readonly(path: Path) -> sqlite3.Connection:
    uri = path.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
    return {str(row["name"]) for row in rows}


def _column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    try:
        return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    except sqlite3.DatabaseError:
        return set()


def _first_existing_column(conn: sqlite3.Connection, table_name: str, candidates: tuple[str, ...]) -> str | None:
    columns = _column_names(conn, table_name)
    for column in candidates:
        if column in columns:
            return column
    return None


def _ontology_exists(conn: sqlite3.Connection, ontology_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM ontology_lenses WHERE ontology_id = ? LIMIT 1", (ontology_id,)).fetchone()
    return row is not None


def _missing_semantic_refs(
    conn: sqlite3.Connection,
    *,
    source_table: str,
    source_alias: str,
    source_id_column: str,
    ref_type_column: str,
    ref_id_column: str,
    ontology_id: str | None,
    required: bool = False,
    require_complete_pair: bool = False,
) -> list[dict[str, Any]]:
    source_columns = _column_names(conn, source_table)
    required_columns = {source_id_column, ref_type_column, ref_id_column}
    if not required_columns <= source_columns:
        return []

    missing: list[dict[str, Any]] = []
    ontology_clause, ontology_params = _ontology_clause(source_alias, ontology_id)
    ref_type_expr = f"TRIM(COALESCE(CAST({source_alias}.{ref_type_column} AS TEXT), ''))"
    ref_id_expr = f"TRIM(COALESCE(CAST({source_alias}.{ref_id_column} AS TEXT), ''))"
    select_prefix = (
        f"SELECT '{source_table}' AS table_name, {source_alias}.{source_id_column} AS source_id, "
        f"{source_alias}.ontology_id, {source_alias}.{ref_type_column} AS ref_type, "
        f"{source_alias}.{ref_id_column} AS ref_id"
    )

    if required:
        missing.extend(
            _rows(
                conn,
                f"{select_prefix}, 'incomplete_required_ref' AS reason "
                f"FROM {source_table} {source_alias} "
                f"WHERE ({ref_type_expr} = '' OR {ref_id_expr} = ''){ontology_clause}",
                ontology_params,
            )
        )
    else:
        missing.extend(
            _rows(
                conn,
                f"{select_prefix}, 'incomplete_ref_pair' AS reason "
                f"FROM {source_table} {source_alias} "
                f"WHERE (({ref_type_expr} = '' AND {ref_id_expr} != '') OR ({ref_type_expr} != '' AND {ref_id_expr} = '')){ontology_clause}",
                ontology_params,
            )
        )

    known_types = tuple(SEMANTIC_REF_TARGETS.keys())
    placeholders = ", ".join("?" for _ in known_types)
    missing.extend(
        _rows(
            conn,
            f"{select_prefix}, 'unknown_ref_type' AS reason "
            f"FROM {source_table} {source_alias} "
            f"WHERE {ref_type_expr} != '' AND {source_alias}.{ref_type_column} NOT IN ({placeholders}){ontology_clause}",
            (*known_types, *ontology_params),
        )
    )

    table_names = _table_names(conn)
    for ref_type, (target_table, key_candidates, same_ontology) in SEMANTIC_REF_TARGETS.items():
        target_key = _first_existing_column(conn, target_table, key_candidates)
        if target_table not in table_names or target_key is None:
            missing.extend(
                _rows(
                    conn,
                    f"{select_prefix}, 'target_table_or_key_missing' AS reason, ? AS expected_table "
                    f"FROM {source_table} {source_alias} "
                    f"WHERE {source_alias}.{ref_type_column} = ? AND {ref_id_expr} != ''{ontology_clause}",
                    (target_table, ref_type, *ontology_params),
                )
            )
            continue

        lens_join = (
            f" AND target.ontology_id = {source_alias}.ontology_id"
            if same_ontology and "ontology_id" in _column_names(conn, target_table)
            else ""
        )
        missing.extend(
            _rows(
                conn,
                f"{select_prefix}, 'missing_ref_target' AS reason, ? AS expected_table, ? AS expected_key "
                f"FROM {source_table} {source_alias} "
                f"LEFT JOIN {target_table} target ON CAST(target.{target_key} AS TEXT) = CAST({source_alias}.{ref_id_column} AS TEXT){lens_join} "
                f"WHERE {source_alias}.{ref_type_column} = ? AND {ref_id_expr} != '' AND target.{target_key} IS NULL{ontology_clause}",
                (target_table, target_key, ref_type, *ontology_params),
            )
        )

    return missing


def _ontology_clause(alias: str, ontology_id: str | None) -> tuple[str, tuple[str, ...]]:
    if not ontology_id:
        return "", ()
    return f" AND {alias}.ontology_id = ?", (ontology_id,)


def _rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [_row_dict(row) for row in conn.execute(sql, params).fetchall()]


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _check(report: dict[str, Any], name: str, passed: bool, detail: dict[str, Any] | None = None) -> None:
    report["checks"].append({"name": name, "status": "pass" if passed else "fail", "detail": detail or {}})


def _error(report: dict[str, Any], code: str, message: str) -> None:
    report["errors"].append({"code": code, "message": message})


def _finalize(report: dict[str, Any]) -> dict[str, Any]:
    if report["errors"]:
        report["status"] = "fail"
    elif report["warnings"]:
        report["status"] = "warning"
    else:
        report["status"] = "pass"
    return report
