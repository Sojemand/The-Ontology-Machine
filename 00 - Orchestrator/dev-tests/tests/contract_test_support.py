from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import orchestrator.orchestrator_contract as contract_module

def _run_contract(tmp_path: Path, payload: dict) -> dict:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = contract_module.main(["--request", str(request_path), "--response", str(response_path)])
    assert exit_code == 0
    return json.loads(response_path.read_text(encoding="utf-8"))

def _insert_document_rows(db_path: Path, rows: list[dict[str, object]]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE documents (
                id TEXT PRIMARY KEY,
                file_name TEXT,
                source_file_path TEXT,
                source_page INTEGER,
                content_hash TEXT,
                is_archived INTEGER DEFAULT 0
            )
            """
        )
        conn.execute("CREATE TABLE embeddings (document_id TEXT)")
        conn.executemany(
            "INSERT INTO documents (id, file_name, source_file_path, source_page, content_hash, is_archived) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    row["id"],
                    row["file_name"],
                    row["source_file_path"],
                    row["source_page"],
                    row["content_hash"],
                    row.get("is_archived", 0),
                )
                for row in rows
            ],
        )
        conn.commit()
    finally:
        conn.close()
