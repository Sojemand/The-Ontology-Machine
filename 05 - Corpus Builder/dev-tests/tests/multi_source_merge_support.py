from __future__ import annotations

import hashlib
import json as jsonlib
import os
from pathlib import Path

import pytest

from corpus_builder.database import connect, ensure_schema


def selection(root: Path, state: str) -> dict:
    return {
        "merge_run_id": "merge_phase19",
        "target_artifact_root": str(root),
        "target_database_path": str(root / "Corpus" / "merged.db"),
        "source_databases": [
            {
                "source_database_id": "db_a",
                "source_database_path": str(root / "source_a.db"),
                "source_artifact_root": str(root / "source_a"),
                "source_state": state,
                "source_semantic_release_id": "release_a",
                "source_semantic_release_version": "v1",
                "source_release_fingerprint": "fp_a",
            },
            {
                "source_database_id": "db_b",
                "source_database_path": str(root / "source_b.db"),
                "source_artifact_root": str(root / "source_b"),
                "source_state": state,
                "source_semantic_release_id": "release_b",
                "source_semantic_release_version": "v1",
                "source_release_fingerprint": "fp_b",
            },
        ],
    }


def link_or_skip(source: Path, link: Path) -> None:
    try:
        os.link(source, link)
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")


def source_database(
    root: Path,
    source_id: str,
    document_id: str,
    content_hash: str,
    *,
    stored_file_path: str | None = None,
) -> None:
    source_root = root / f"source_{source_id[-1]}"
    original = source_root / "Documents" / "originals" / f"{document_id}.pdf"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(f"{source_id}:{document_id}".encode("utf-8"))
    db_path = root / f"source_{source_id[-1]}.db"
    conn = connect(str(db_path))
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO documents (id, file_name, file_path, source_file_path, content_hash, document_type, category, language, model, model_confidence, materialization_version, projection_id, projection_fingerprint, validator_status, loaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (
                document_id,
                f"{document_id}.pdf",
                stored_file_path or str(original),
                stored_file_path or str(original),
                content_hash,
                "invoice",
                "finance",
                "de",
                "test-model",
                0.9,
                "v1",
                f"projection_{source_id}",
                f"sha256:projection_{source_id}",
                "pass",
            ),
        )
        conn.execute(
            "INSERT INTO document_payloads (document_id, schema_version, structured_json, normalized_json, release_fingerprint, loaded_at) "
            "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (document_id, "test.v1", "{}", "{}", f"fp_{source_id[-1]}"),
        )
        conn.execute(
            "INSERT INTO document_processing_state (document_id, schema_version, materialization_version, materialized_snapshot_id, projection_id, projection_fingerprint, materialization_state, source_mode, last_materialized_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (
                document_id,
                "state.v1",
                "v1",
                f"fp_{source_id[-1]}",
                f"projection_{source_id}",
                f"sha256:projection_{source_id}",
                "current",
                "structured",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def request_fingerprint(payload: dict[str, object]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = jsonlib.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def load_artifact_json(artifact_root: Path, ref: dict) -> dict:
    return jsonlib.loads((artifact_root / str(ref["artifact_path"])).read_text(encoding="utf-8"))
