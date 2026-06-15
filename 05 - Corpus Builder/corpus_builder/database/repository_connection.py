"""Connection helpers for corpus.db access."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with the repo's standard pragmas."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def connect_readonly(db_path: str) -> sqlite3.Connection:
    """Open an existing SQLite database without changing journal mode."""
    try:
        return _connect_readonly_uri(db_path, immutable=False)
    except sqlite3.OperationalError as exc:
        if "unable to open database file" not in str(exc).lower():
            raise
        return _connect_readonly_uri(db_path, immutable=True)


def _connect_readonly_uri(db_path: str, *, immutable: bool) -> sqlite3.Connection:
    query = "?mode=ro&immutable=1" if immutable else "?mode=ro"
    uri = Path(db_path).resolve(strict=False).as_uri() + query
    conn = sqlite3.connect(uri, check_same_thread=False, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
    except Exception:
        conn.close()
        raise
    return conn


__all__ = ["connect", "connect_readonly"]
