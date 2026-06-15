"""Named data carriers and constants for corpus export stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CSV_FIELDNAMES = [
    "id",
    "file_name",
    "document_type",
    "category",
    "model_confidence",
    "validator_status",
    "language",
    "projection_id",
    "materialization_state",
    "materialization_version",
    "tags",
    "people",
    "organizations",
    "promotions_json",
]


@dataclass(slots=True)
class ExportDocumentSnapshot:
    id: str
    file_name: str | None
    file_path: str | None
    content_hash: str | None
    document_type: str | None
    category: str | None
    subcategory: str | None
    language: str | None
    model_confidence: float | int | None
    validator_status: str | None
    projection_id: str | None
    projection_fingerprint: str | None
    materialization_state: str | None
    materialization_version: str | None
    loaded_at: str | None
    fields: dict[str, Any]
    rows: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    tags: list[str]
    people: list[str]
    organizations: list[str]
    entities: list[dict[str, Any]]
    document_promotions: list[dict[str, Any]]
    document_promotion_values: dict[str, Any]
    processing_state: dict[str, Any] | None
