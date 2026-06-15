"""Document record mapping for the loader domain."""

from __future__ import annotations

import json
from pathlib import Path

from ..models.source_identity import build_source_document_identity, parse_source_identity
from ..models.serialization import now_iso
from .types import JsonDict, PreparedBundle
from .preparation import _mapping_block, content_free_text, prefer_mapping_value
from .review_policy import coerce_issue_count, overall_needs_review, payload_review_state


def build_document(
    document_id: str,
    prepared: PreparedBundle,
    content_hash: str,
    file_path: str,
    *,
    normalized_json: JsonDict | None = None,
    projection_meta: JsonDict | None = None,
    release: JsonDict | None = None,
) -> JsonDict:
    preferred_json = prepared.preferred_json
    structured_json = prepared.structured_payload
    source_payload = preferred_json if isinstance(preferred_json.get("source"), dict) else structured_json
    source = _mapping_block(source_payload, "source")
    source_identity = parse_source_identity(file_path, preferred_json, structured_json)
    source_document_identity = build_source_document_identity(
        file_path,
        content_hash,
        preferred_json,
        structured_json,
    )
    classification = _mapping_block(preferred_json, "classification")
    fallback_classification = _mapping_block(structured_json, "classification")
    context = _mapping_block(preferred_json, "context")
    fallback_context = _mapping_block(structured_json, "context")
    processing = _mapping_block(preferred_json, "processing")
    fallback_processing = _mapping_block(structured_json, "processing")
    interpreter_needs_review, interpreter_review_reason = payload_review_state(structured_json)
    normalizer_needs_review, normalizer_review_reason = payload_review_state(normalized_json or {})
    structure = _mapping_block(_mapping_block(preferred_json, "content"), "structure") or _mapping_block(
        _mapping_block(structured_json, "content"),
        "structure",
    )
    issue_count = coerce_issue_count(prepared.validation_payload)
    validator_status = str(prepared.validation_payload.get("result", "")).strip().lower() or ("warn" if issue_count > 0 else "pass")
    doc = {
        "id": document_id,
        "file_name": source.get("file_name", Path(file_path).name),
        "file_path": file_path,
        "source_file_path": source_identity.source_file_path,
        "source_page": source_identity.source_page,
        "source_page_count": source_identity.source_page_count,
        "source_document_id": source_document_identity.source_document_id,
        "source_uri": source_document_identity.source_uri,
        "source_file_id": source_document_identity.source_file_id,
        "source_artifact_id": source_document_identity.source_artifact_id,
        "ingest_run_id": source_document_identity.ingest_run_id,
        "page_index": source_document_identity.page_index,
        "page_label": source_document_identity.page_label,
        "materialization_order": source_document_identity.materialization_order,
        "page_content_hash": source_document_identity.page_content_hash,
        "source_content_hash": source_document_identity.source_content_hash,
        "content_hash": content_hash,
        "file_size_bytes": source.get("size_bytes"),
        "document_type": prefer_mapping_value(classification, fallback_classification, "document_type") or "other",
        "document_type_confidence": prefer_mapping_value(classification, fallback_classification, "document_type_confidence"),
        "category": prefer_mapping_value(classification, fallback_classification, "category") or "other",
        "subcategory": prefer_mapping_value(classification, fallback_classification, "subcategory"),
        "language": prefer_mapping_value(classification, fallback_classification, "language") or "und",
        "is_scan": int(bool(prefer_mapping_value(classification, fallback_classification, "is_scan") or False)),
        "has_handwriting": int(bool(prefer_mapping_value(classification, fallback_classification, "has_handwriting") or False)),
        "page_count": prefer_mapping_value(classification, fallback_classification, "page_count") or 1,
        "model": prefer_mapping_value(processing, fallback_processing, "model") or "unknown",
        "model_confidence": prefer_mapping_value(processing, fallback_processing, "model_confidence", "confidence") or 0.0,
        "needs_review": int(
            overall_needs_review(
                structured_payload=structured_json,
                normalized_payload=normalized_json,
                validation_report=prepared.validation_payload,
                issue_count=issue_count,
            )
        ),
        "interpreter_needs_review": int(interpreter_needs_review),
        "interpreter_review_reason": interpreter_review_reason or None,
        "normalizer_needs_review": int(normalizer_needs_review),
        "normalizer_review_reason": normalizer_review_reason or None,
        "vision_used": int(bool(prefer_mapping_value(processing, fallback_processing, "vision_used") or False)),
        "validator_status": validator_status,
        "validator_issues_count": issue_count,
        "content_structure": structure.get("type") if isinstance(structure, dict) else str(structure) if structure else None,
        "content_fields_json": json.dumps(prepared.sanitized_fields, ensure_ascii=False) if prepared.sanitized_fields else None,
        "content_rows_json": json.dumps(prepared.sanitized_rows, ensure_ascii=False) if prepared.sanitized_rows else None,
        "content_free_text": content_free_text(preferred_json) or content_free_text(structured_json),
        "loaded_at": now_iso(),
        "materialization_version": str((release or {}).get("materialization_version") or ""),
        "projection_id": str((projection_meta or {}).get("projection_id") or ""),
        "projection_fingerprint": str((projection_meta or {}).get("projection_fingerprint") or ""),
    }
    return doc


__all__ = ["build_document"]
