"""Aggregate query helpers for corpus.db."""

from __future__ import annotations

import sqlite3

from .validation import ensure_column_name, ensure_table_name


def count(conn: sqlite3.Connection, table: str, where: str | None = None) -> int:
    sql = f"SELECT COUNT(*) FROM {ensure_table_name(table)}"
    if where:
        sql += f" WHERE {where}"
    return conn.execute(sql).fetchone()[0]


def group_count(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    where: str | None = None,
) -> dict[str, int]:
    table_name = ensure_table_name(table)
    column_name = ensure_column_name(column)
    sql = f"SELECT {column_name}, COUNT(*) as cnt FROM {table_name}"
    if where:
        sql += f" WHERE {where}"
    sql += f" GROUP BY {column_name} ORDER BY cnt DESC"
    return {str(row[0] or "null"): row[1] for row in conn.execute(sql)}


def top_n(conn: sqlite3.Connection, table: str, column: str, n: int = 20) -> list[tuple[str, int]]:
    table_name = ensure_table_name(table)
    column_name = ensure_column_name(column)
    sql = f"SELECT {column_name}, COUNT(*) as cnt FROM {table_name} GROUP BY {column_name} ORDER BY cnt DESC LIMIT ?"
    return [(str(row[0]), row[1]) for row in conn.execute(sql, (n,))]


def avg(conn: sqlite3.Connection, table: str, column: str, where: str | None = None) -> float | None:
    sql = f"SELECT AVG({ensure_column_name(column)}) FROM {ensure_table_name(table)}"
    if where:
        sql += f" WHERE {where}"
    result = conn.execute(sql).fetchone()[0]
    return float(result) if result is not None else None


def sum_col(conn: sqlite3.Connection, table: str, column: str, where: str | None = None) -> float | None:
    sql = f"SELECT SUM({ensure_column_name(column)}) FROM {ensure_table_name(table)}"
    if where:
        sql += f" WHERE {where}"
    result = conn.execute(sql).fetchone()[0]
    return float(result) if result is not None else None


def min_col(conn: sqlite3.Connection, table: str, column: str, where: str | None = None) -> str | None:
    sql = f"SELECT MIN({ensure_column_name(column)}) FROM {ensure_table_name(table)}"
    if where:
        sql += f" WHERE {where}"
    result = conn.execute(sql).fetchone()[0]
    return str(result) if result is not None else None


def max_col(conn: sqlite3.Connection, table: str, column: str, where: str | None = None) -> str | None:
    sql = f"SELECT MAX({ensure_column_name(column)}) FROM {ensure_table_name(table)}"
    if where:
        sql += f" WHERE {where}"
    result = conn.execute(sql).fetchone()[0]
    return str(result) if result is not None else None


def group_sum(
    conn: sqlite3.Connection,
    table: str,
    group_col: str,
    value_col: str,
    where: str | None = None,
) -> dict[str, float]:
    table_name = ensure_table_name(table)
    group_name = ensure_column_name(group_col)
    value_name = ensure_column_name(value_col)
    sql = f"SELECT {group_name}, SUM({value_name}) as total FROM {table_name}"
    if where:
        sql += f" WHERE {where}"
    sql += f" GROUP BY {group_name} ORDER BY total DESC"
    return {
        str(row[0] or "null"): float(row[1]) if row[1] is not None else 0.0
        for row in conn.execute(sql)
    }


__all__ = [
    "avg",
    "count",
    "group_count",
    "group_sum",
    "max_col",
    "min_col",
    "sum_col",
    "top_n",
]
