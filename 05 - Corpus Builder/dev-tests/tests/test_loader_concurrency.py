"""Loader concurrency and contention tests."""

from __future__ import annotations

import threading

import pytest

from corpus_builder.database import connect, ensure_schema
from tests.fixtures.loader_io import load_input_file, vision_report_path, write_structured_pair


def test_concurrent_loads_keep_one_active_document_per_file_path(vision_structured, vision_validation_report, tmp_path):
    db_path = tmp_path / "corpus.db"
    init_conn = connect(str(db_path))
    ensure_schema(init_conn)
    init_conn.close()
    barrier = threading.Barrier(2)
    results: list[tuple[str, str, str | None]] = []
    result_lock = threading.Lock()

    def _worker(doc_id: str) -> None:
        conn = connect(str(db_path))
        ensure_schema(conn)
        structured = dict(vision_structured)
        structured["source"] = dict(vision_structured["source"])
        structured["source"]["content_hash"] = f"sha256:{doc_id}"
        json_path = write_structured_pair(tmp_path, doc_id, structured, vision_validation_report)
        barrier.wait()
        result = load_input_file(conn, json_path, validation_path=vision_report_path(json_path))
        with result_lock:
            results.append((doc_id, result.status, result.reason))
        conn.close()

    threads = [threading.Thread(target=_worker, args=(doc_id,)) for doc_id in ("race_a", "race_b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    conn = connect(str(db_path))
    rows = conn.execute("SELECT id, is_archived, superseded_by FROM documents ORDER BY id").fetchall()
    conn.close()

    assert sorted(status for _, status, _ in results) == ["archived_and_loaded", "loaded"]
    assert sum(1 for row in rows if row["is_archived"] == 0) == 1
    assert sum(1 for row in rows if row["is_archived"] == 1) == 1
    archived_row = next(row for row in rows if row["is_archived"] == 1)
    active_row = next(row for row in rows if row["is_archived"] == 0)
    assert archived_row["superseded_by"] == active_row["id"]


@pytest.mark.stress
def test_repeated_concurrent_loads_keep_single_active_document(vision_structured, vision_validation_report, tmp_path):
    for iteration in range(5):
        db_path = tmp_path / f"stress-{iteration}.db"
        init_conn = connect(str(db_path))
        ensure_schema(init_conn)
        init_conn.close()
        barrier = threading.Barrier(2)

        def _worker(doc_id: str) -> None:
            conn = connect(str(db_path))
            ensure_schema(conn)
            structured = dict(vision_structured)
            structured["source"] = dict(vision_structured["source"])
            structured["source"]["content_hash"] = f"sha256:{iteration}-{doc_id}"
            json_path = write_structured_pair(tmp_path, f"{iteration}-{doc_id}", structured, vision_validation_report)
            barrier.wait()
            load_input_file(conn, json_path, validation_path=vision_report_path(json_path))
            conn.close()

        threads = [threading.Thread(target=_worker, args=(doc_id,)) for doc_id in ("left", "right")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        conn = connect(str(db_path))
        active_count = conn.execute("SELECT COUNT(*) FROM documents WHERE is_archived = 0").fetchone()[0]
        archived_count = conn.execute("SELECT COUNT(*) FROM documents WHERE is_archived = 1").fetchone()[0]
        conn.close()

        assert active_count == 1
        assert archived_count == 1
