from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from corpus_builder.database import connect, ensure_schema
from corpus_builder.pipeline_batches.path_io import ensure_directory, write_json
from corpus_builder.semantic_release.multi_source_merge_types import path_hash


def artifact_tree(root: Path) -> None:
    for relative in ("Input", "Corpus", "Semantic Release", "Documents/logs", "Documents/originals"):
        (root / relative).mkdir(parents=True, exist_ok=True)


def link_or_skip(source: Path, link: Path) -> None:
    try:
        os.link(source, link)
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")


def final_manifest(root: Path) -> Path:
    batch_root = root / "Documents" / "logs" / "pipeline_batches" / "pbt_20260506010101_deadbeef_1"
    ensure_directory(batch_root)
    source = root.parent / "source_a.pdf"
    source.write_bytes(b"pdf")
    normalized = root / "Documents" / "normalized" / "doc_1.json"
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text("{}", encoding="utf-8")
    database_path = root / "Corpus" / "active.db"
    active_database(database_path, normalized)
    manifest = {
        "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
        "manifest_fingerprint": "sha256:test",
        "batch_kind": "sample_ingest",
        "active_database": {"database_path": str(database_path), "database_path_hash": path_hash(database_path)},
        "record_counts": {"documents": 1},
        "input_files": [{"source_path": str(source), "original_ref": str(source), "content_hash": "sha256:source_a"}],
        "materialized_records": [{"document_id": "doc_1", "record_id": "rec_1", "artifact_refs": [{"artifact_path": "Documents/normalized/doc_1.json"}]}],
    }
    path = batch_root / "pipeline_batch_manifest.json"
    write_json(path, manifest)
    return path


def active_database(database_path: Path, normalized: Path) -> None:
    conn = connect(str(database_path))
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO documents (id, file_name, file_path, source_file_path, content_hash, document_type, category, language, model, model_confidence, materialization_version, projection_id, projection_fingerprint, validator_status, loaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (
                "doc_1",
                "doc_1.pdf",
                str(normalized),
                str(normalized),
                "sha256:source_a",
                "invoice",
                "finance",
                "de",
                "test-model",
                0.9,
                "v1",
                "projection_default",
                "sha256:projection",
                "pass",
            ),
        )
        conn.execute(
            "INSERT INTO document_payloads (document_id, schema_version, structured_json, normalized_json, loaded_at) "
            "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            ("doc_1", "test.v1", "{}", "{}"),
        )
        conn.commit()
    finally:
        conn.close()


def request_fingerprint(payload: dict[str, object]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
