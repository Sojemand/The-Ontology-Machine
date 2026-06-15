"""Shared deterministic helpers for basic relation mining."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentRow:
    document_id: str
    source_document_id: str
    source_uri: str
    source_file_id: str | None
    source_artifact_id: str
    ingest_run_id: str
    page_index: int
    page_label: str | None
    source_page_count: int | None
    materialization_order: int
    page_content_hash: str
    source_content_hash: str
    file_name: str
    document_type: str
    document_type_confidence: float | None
    category: str
    subcategory: str | None
    release_document_type: str | None
    release_document_type_confidence: float | None
    release_category: str | None
    release_subcategory: str | None


def as_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def clean_text(value: Any) -> str | None:
    if is_blank(value):
        return None
    return str(value).strip()


def clean_confidence(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    return min(1.0, max(0.0, confidence))


def short_hash(*parts: str) -> str:
    text = "\x1f".join(str(part or "") for part in parts)
    return sha256(text.encode("utf-8")).hexdigest()[:20]


def base_unit_id(source_document_id: str) -> str:
    return f"su_base_{short_hash(source_document_id)}"


def page_unit_id(document_id: str) -> str:
    return f"su_page_{short_hash(document_id)}"


def structural_relation_id(relation_type: str, source_unit_id: str, target_unit_id: str) -> str:
    return f"sur_{short_hash(relation_type, source_unit_id, target_unit_id)}"


def fetch_documents(conn: sqlite3.Connection) -> tuple[list[DocumentRow], list[dict[str, Any]]]:
    rows = conn.execute(
        "SELECT d.id, d.file_name, d.document_type, d.document_type_confidence, d.category, d.subcategory, "
        "d.source_document_id, d.source_uri, d.source_file_id, "
        "d.source_artifact_id, d.ingest_run_id, d.page_index, d.page_label, d.source_page_count, "
        "d.materialization_order, d.page_content_hash, d.source_content_hash, payload.normalized_json "
        "FROM documents d LEFT JOIN document_payloads payload ON payload.document_id = d.id "
        "WHERE COALESCE(d.is_archived, 0) = 0 ORDER BY d.source_document_id, d.page_index, d.materialization_order, d.id"
    ).fetchall()
    valid: list[DocumentRow] = []
    unresolved: list[dict[str, Any]] = []
    required = (
        "source_document_id",
        "source_uri",
        "source_artifact_id",
        "ingest_run_id",
        "page_content_hash",
        "source_content_hash",
    )
    for row in rows:
        missing = [field for field in required if is_blank(row[field])]
        if row["page_index"] is None:
            missing.append("page_index")
        if missing:
            unresolved.append(
                {
                    "document_id": row["id"],
                    "missing": missing,
                    "file_name": row["file_name"],
                }
            )
            continue
        valid.append(_document_from_row(row))
    return valid, unresolved


def group_documents(
    documents: list[DocumentRow],
) -> tuple[dict[str, list[DocumentRow]], list[dict[str, Any]]]:
    grouped: dict[str, list[DocumentRow]] = defaultdict(list)
    for document in documents:
        grouped[document.source_document_id].append(document)
    accepted: dict[str, list[DocumentRow]] = {}
    rejected: list[dict[str, Any]] = []
    for source_document_id, group in grouped.items():
        by_page: dict[int, list[str]] = defaultdict(list)
        for document in group:
            by_page[document.page_index].append(document.document_id)
        duplicate_pages = {
            page_index: document_ids
            for page_index, document_ids in by_page.items()
            if len(document_ids) > 1
        }
        if duplicate_pages:
            rejected.append(
                {
                    "source_document_id": source_document_id,
                    "reason": "duplicate_page_index",
                    "duplicates": duplicate_pages,
                }
            )
            continue
        accepted[source_document_id] = sorted(
            group,
            key=lambda item: (item.page_index, item.materialization_order, item.document_id),
        )
    return accepted, rejected


def _classification_from_payload(raw_json: Any) -> dict[str, Any]:
    if is_blank(raw_json):
        return {}
    try:
        payload = json.loads(str(raw_json))
    except json.JSONDecodeError:
        return {}
    classification = payload.get("classification") if isinstance(payload, dict) else {}
    return classification if isinstance(classification, dict) else {}


def _document_from_row(row: sqlite3.Row) -> DocumentRow:
    release_classification = _classification_from_payload(row["normalized_json"])
    return DocumentRow(
        document_id=str(row["id"]),
        source_document_id=str(row["source_document_id"] or ""),
        source_uri=str(row["source_uri"] or ""),
        source_file_id=str(row["source_file_id"] or "") or None,
        source_artifact_id=str(row["source_artifact_id"] or ""),
        ingest_run_id=str(row["ingest_run_id"] or ""),
        page_index=int(row["page_index"]),
        page_label=str(row["page_label"] or "") or None,
        source_page_count=int(row["source_page_count"]) if row["source_page_count"] is not None else None,
        materialization_order=int(row["materialization_order"]),
        page_content_hash=str(row["page_content_hash"] or ""),
        source_content_hash=str(row["source_content_hash"] or ""),
        file_name=str(row["file_name"] or ""),
        document_type=str(row["document_type"] or ""),
        document_type_confidence=clean_confidence(row["document_type_confidence"]),
        category=str(row["category"] or ""),
        subcategory=clean_text(row["subcategory"]),
        release_document_type=clean_text(release_classification.get("document_type")),
        release_document_type_confidence=clean_confidence(release_classification.get("document_type_confidence")),
        release_category=clean_text(release_classification.get("category")),
        release_subcategory=clean_text(release_classification.get("subcategory")),
    )
