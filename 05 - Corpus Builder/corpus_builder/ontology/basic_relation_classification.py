"""Source-document classification materialization for basic relation mining."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .basic_relation_support import DocumentRow, clean_confidence, clean_text


def insert_source_document_classifications(conn: sqlite3.Connection, group: list[DocumentRow]) -> int:
    inserted = 0
    source_document_id = group[0].source_document_id
    for scope in ("base", "semantic_release"):
        pages = _classification_pages(group, scope=scope)
        status, reason = _classification_status(pages)
        basis_json = {
            "basis": pages[0]["basis"] if pages else scope,
            "source_document_id": source_document_id,
            "status_reason": reason,
            "page_count": len(pages),
            "field_distributions": {
                "document_type": _field_distribution(pages, "document_type"),
                "category": _field_distribution(pages, "category"),
                "subcategory": _field_distribution(pages, "subcategory"),
            },
            "pages": pages,
        }
        conn.execute(
            "INSERT INTO source_document_classifications (source_document_id, classification_scope, ontology_id, "
            "document_type, category, subcategory, confidence, status, basis_json, created_by, created_at, updated_at) "
            "VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 'basic_relation_mining', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (
                source_document_id,
                scope,
                _consensus_value(pages, "document_type"),
                _consensus_value(pages, "category"),
                _consensus_value(pages, "subcategory"),
                _classification_confidence(pages, status),
                status,
                json.dumps(basis_json, ensure_ascii=False),
            ),
        )
        inserted += 1
    return inserted


def _classification_pages(group: list[DocumentRow], *, scope: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for document in group:
        if scope == "semantic_release":
            document_type = document.release_document_type
            category = document.release_category
            subcategory = document.release_subcategory
            confidence = document.release_document_type_confidence
            basis = "document_payloads.normalized_json.classification"
        else:
            document_type = clean_text(document.document_type)
            category = clean_text(document.category)
            subcategory = clean_text(document.subcategory)
            confidence = document.document_type_confidence
            basis = "documents.classification_fields"
        pages.append(
            {
                "document_id": document.document_id,
                "page_index": document.page_index,
                "document_type": document_type,
                "category": category,
                "subcategory": subcategory,
                "confidence": confidence,
                "basis": basis,
            }
        )
    return pages


def _field_distribution(pages: list[dict[str, Any]], field: str) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for page in pages:
        value = clean_text(page.get(field)) or ""
        key = value if value else "<blank>"
        distribution[key] = distribution.get(key, 0) + 1
    return dict(sorted(distribution.items()))


def _has_other(value: Any) -> bool:
    return str(value or "").strip().lower() == "other"


def _consensus_value(pages: list[dict[str, Any]], field: str) -> str | None:
    values = {clean_text(page.get(field)) for page in pages}
    values.discard(None)
    if len(values) != 1:
        return None
    value = next(iter(values))
    return None if _has_other(value) else value


def _classification_status(pages: list[dict[str, Any]]) -> tuple[str, str]:
    required_fields = ("document_type", "category")
    classification_fields = ("document_type", "category", "subcategory")
    for field in classification_fields:
        non_blank_values = {clean_text(page.get(field)) for page in pages if clean_text(page.get(field))}
        if len(non_blank_values) > 1:
            return "ambiguous", f"conflicting_{field}"
    if any(not clean_text(page.get(field)) for page in pages for field in required_fields):
        return "unresolved", "missing_required_classification_value"
    if any(_has_other(page.get(field)) for page in pages for field in classification_fields):
        return "unresolved", "contains_other_fallback"
    return "materialized", "all_pages_consistent"


def _classification_confidence(pages: list[dict[str, Any]], status: str) -> float | None:
    confidences = [
        confidence
        for confidence in (clean_confidence(page.get("confidence")) for page in pages)
        if confidence is not None
    ]
    if confidences:
        return min(confidences)
    return 1.0 if status == "materialized" else None
