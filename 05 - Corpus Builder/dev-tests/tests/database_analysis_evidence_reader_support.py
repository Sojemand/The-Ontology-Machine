from __future__ import annotations

import hashlib
import json
from pathlib import Path

from corpus_builder.database.repository_connection import connect
from corpus_builder.database.workflow import ensure_schema


def artifact_tree(root: Path) -> None:
    for relative in (
        "Input",
        "Corpus",
        "Semantic Release",
        "Documents/logs",
        "Documents/structured",
        "Documents/normalized",
        "Documents/originals",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)


def database(root: Path, *, active_release_fingerprint: str = "fp_release") -> Path:
    db_path = root / "Corpus" / "active.db"
    conn = connect(str(db_path))
    try:
        ensure_schema(conn)
        conn.execute(
            """
            UPDATE installation_state
            SET active_release_id = ?, active_release_version = ?, active_release_fingerprint = ?, updated_at = CURRENT_TIMESTAMP
            WHERE singleton = 1
            """,
            ("release_a", "v1", active_release_fingerprint),
        )
        conn.execute(
            """
            INSERT INTO documents (
                id, file_name, file_path, source_file_path, content_hash, document_type, category, model, model_confidence,
                needs_review, interpreter_needs_review, normalizer_needs_review, projection_id, projection_fingerprint,
                validator_status, validator_issues_count, loaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "doc_1",
                "invoice.pdf",
                str(root / "Documents" / "structured" / "invoice.structured.json"),
                str(root / "Documents" / "originals" / "invoice.pdf"),
                "hash_doc_1",
                "invoice",
                "finance",
                "test-model",
                0.99,
                1,
                0,
                1,
                "projection_a",
                "fp_projection_a",
                "warning",
                2,
            ),
        )
        conn.execute(
            """
            INSERT INTO document_payloads (
                document_id, schema_version, structured_json, normalized_json, projection_json, release_fingerprint, loaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "doc_1",
                "kernel.document_payload.v1",
                '{"structured": true}',
                '{"normalized": true}',
                '{"projection": true}',
                active_release_fingerprint,
            ),
        )
        conn.execute(
            """
            INSERT INTO document_processing_state (
                document_id, schema_version, materialization_version, materialized_snapshot_id, projection_id,
                projection_fingerprint, materialization_state, source_mode, last_materialized_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            ("doc_1", "kernel.document_processing_state.v1", "mv1", "snapshot_1", "projection_a", "fp_projection_a", "current", "structured"),
        )
        conn.execute(
            "INSERT INTO evidence_atoms (document_id, atom_type, json_path, source_ref, text_value) VALUES (?, ?, ?, ?, ?)",
            ("doc_1", "field", "$.total", "Documents/structured/invoice.structured.json", "19.99"),
        )
        candidate_cursor = conn.execute(
            """
            INSERT INTO slot_candidates (document_id, slot, display_value, strategy, confidence, is_projection_backed, source_refs_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("doc_1", "total_amount", "19.99", "semantic_projection", 0.92, 1, '["Documents/structured/invoice.structured.json"]'),
        )
        conn.execute(
            """
            INSERT INTO document_promotions (
                document_id, slot, slot_label, value_type, query_role, display_value, normalized_value, compact_value,
                numeric_value, ordinal, confidence, candidate_id, source_path, source_refs_json, projection_id,
                release_fingerprint, materialization_version, is_current, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "doc_1",
                "total_amount",
                "Total Amount",
                "number_or_money_string",
                "amount",
                "19.99 EUR",
                "19.99",
                "19.99",
                19.99,
                0,
                0.92,
                candidate_cursor.lastrowid,
                "content.fields.total_amount",
                '["Documents/structured/invoice.structured.json"]',
                "projection_a",
                active_release_fingerprint,
                "mv1",
                1,
            ),
        )
        conn.execute(
            """
            INSERT INTO document_entities (
                document_id, entity_key, entity_type, display_value, source_path, projection_id, materialization_version, state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("doc_1", "invoice.total", "amount", "19.99", "content.fields.total_amount", "projection_a", "mv1", "materialized"),
        )
        conn.execute(
            "INSERT INTO materialization_audit (created_at, level, code, document_id, projection_id, message, details_json) VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)",
            ("warning", "projection_gap", "doc_1", "projection_a", "Projected field needs review.", "{}"),
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def owner_request(owner_action: str, **fields: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": owner_action,
        "workflow_run_id": "wr_analysis",
        "adapter_call_id": "adc_analysis",
        "requested_at": "2026-05-07T00:00:00Z",
        "target_identity": {"database_path_hash": "sha256:test"},
        **fields,
    }
    payload["request_fingerprint"] = request_fingerprint(payload)
    return payload


def request_fingerprint(payload: dict[str, object]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
