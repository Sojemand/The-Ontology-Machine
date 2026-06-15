from __future__ import annotations

import sqlite3
from pathlib import Path


def insert_corpus_hash(db_path: Path, content_hash: str, *, archived: bool = False) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS documents (content_hash TEXT NOT NULL, is_archived BOOLEAN DEFAULT 0)")
        conn.execute(
            "INSERT INTO documents (content_hash, is_archived) VALUES (?, ?)",
            (content_hash, 1 if archived else 0),
        )
