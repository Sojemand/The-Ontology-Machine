from __future__ import annotations

import json


def insert_document(
    db,
    document_id: str,
    *,
    source_document_id: str = "source-a",
    source_uri: str = "source-a.pdf",
    source_artifact_id: str = "source-a.pdf",
    page_index: int = 0,
    page_label: str = "1",
    materialization_order: int | None = None,
    content_hash: str | None = None,
    document_type: str = "page",
    document_type_confidence: float | None = None,
    category: str = "test",
    subcategory: str | None = None,
) -> None:
    hash_value = content_hash or f"sha256:{document_id}"
    db.execute(
        "INSERT INTO documents (id, file_name, file_path, source_file_path, source_page, source_page_count, "
        "source_document_id, source_uri, source_artifact_id, ingest_run_id, page_index, page_label, "
        "materialization_order, page_content_hash, source_content_hash, content_hash, document_type, category, "
        "subcategory, document_type_confidence, model, model_confidence, validator_status, loaded_at) "
        "VALUES (?, ?, ?, ?, ?, 3, ?, ?, ?, 'run-test', ?, ?, ?, ?, 'sha256:source-a', ?, "
        "?, ?, ?, ?, 'test-model', 1.0, 'ok', CURRENT_TIMESTAMP)",
        (
            document_id,
            f"{document_id}.pdf",
            f"{source_uri}::page={page_index + 1:03d}-of-003",
            source_uri,
            page_index + 1,
            source_document_id,
            source_uri,
            source_artifact_id,
            page_index,
            page_label,
            page_index if materialization_order is None else materialization_order,
            hash_value,
            hash_value,
            document_type,
            category,
            subcategory,
            document_type_confidence,
        ),
    )


def insert_payload_classification(
    db,
    document_id: str,
    *,
    document_type: str,
    category: str,
    subcategory: str | None = None,
    document_type_confidence: float | None = None,
) -> None:
    db.execute(
        "INSERT INTO document_payloads (document_id, structured_json, normalized_json, loaded_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (
            document_id,
            "{}",
            json.dumps(
                {
                    "classification": {
                        "document_type": document_type,
                        "document_type_confidence": document_type_confidence,
                        "category": category,
                        "subcategory": subcategory,
                    }
                },
                ensure_ascii=False,
            ),
        ),
    )
