"""Pure shape-mapping logic for corpus export formats."""

from __future__ import annotations

import json
from typing import Any

from .types import ExportDocumentSnapshot


def build_jsonl_record(snapshot: ExportDocumentSnapshot) -> dict[str, Any]:
    return {
        "id": snapshot.id,
        "file_name": snapshot.file_name,
        "file_path": snapshot.file_path,
        "content_hash": snapshot.content_hash,
        "document_type": snapshot.document_type,
        "category": snapshot.category,
        "subcategory": snapshot.subcategory,
        "language": snapshot.language,
        "model_confidence": snapshot.model_confidence,
        "validator_status": snapshot.validator_status,
        "projection_id": snapshot.projection_id,
        "materialization_state": snapshot.materialization_state,
        "materialization_version": snapshot.materialization_version,
        "loaded_at": snapshot.loaded_at,
        "fields": snapshot.fields,
        "rows": snapshot.rows,
        "relations": snapshot.relations,
        "tags": snapshot.tags,
        "people": snapshot.people,
        "organizations": snapshot.organizations,
        "entities": snapshot.entities,
        "document_promotions": snapshot.document_promotions,
        "document_promotion_values": snapshot.document_promotion_values,
        "processing_state": snapshot.processing_state,
    }


def build_csv_record(snapshot: ExportDocumentSnapshot) -> dict[str, Any]:
    return {
        "id": snapshot.id,
        "file_name": snapshot.file_name,
        "document_type": snapshot.document_type,
        "category": snapshot.category,
        "model_confidence": snapshot.model_confidence,
        "validator_status": snapshot.validator_status,
        "language": snapshot.language,
        "projection_id": snapshot.projection_id,
        "materialization_state": snapshot.materialization_state,
        "materialization_version": snapshot.materialization_version,
        "tags": ";".join(snapshot.tags),
        "people": ";".join(snapshot.people),
        "organizations": ";".join(snapshot.organizations),
        "promotions_json": json.dumps(snapshot.document_promotion_values, ensure_ascii=False, sort_keys=True),
    }
