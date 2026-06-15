from __future__ import annotations

import sqlite3
from pathlib import Path


def probe_tables(database_path: Path) -> list[str]:
    with sqlite3.connect(str(database_path)) as connection:
        rows = connection.execute("select name from sqlite_master where type = 'table' order by name").fetchall()
    return [str(row[0]) for row in rows]
