"""Types and static specs for the corpus loader pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

JsonDict = dict[str, Any]
ProvenanceMap = dict[str, tuple[str, str]]


@dataclass(slots=True)
class LoadedBundle:
    document_id: str
    structured_json: JsonDict | None
    raw_json: JsonDict | None
    normalized_json: JsonDict | None
    validation_report: JsonDict
    content_hash: str
    file_path: str


@dataclass(slots=True)
class PreparedBundle:
    structured_payload: JsonDict
    preferred_json: JsonDict
    validation_payload: JsonDict
    source_mode: str
    evidence_payload: JsonDict
    field_provenance: ProvenanceMap
    structured_fields: JsonDict
    sanitized_fields: JsonDict
    sanitized_rows: list[JsonDict]
    sanitized_segments: list[JsonDict]
    sanitized_relations: list[JsonDict]
    tags: list[str]
    people: list[str]
    orgs: list[str]


DOCUMENT_COLUMNS = (
    "id", "file_name", "file_path", "source_file_path", "source_page", "source_page_count",
    "source_document_id", "source_uri", "source_file_id", "source_artifact_id", "ingest_run_id",
    "page_index", "page_label", "materialization_order", "page_content_hash", "source_content_hash",
    "content_hash", "file_size_bytes", "document_type", "document_type_confidence",
    "category", "subcategory", "language", "is_scan", "has_handwriting", "page_count",
    "model", "model_confidence", "needs_review", "interpreter_needs_review",
    "interpreter_review_reason", "normalizer_needs_review", "normalizer_review_reason",
    "vision_used", "materialization_version", "projection_id", "projection_fingerprint",
    "validator_status", "validator_issues_count",
    "content_structure", "content_fields_json", "content_rows_json", "content_free_text", "loaded_at",
)
NORMALIZED_LIST_KEYS = {"tags": ("tag", "name", "value"), "people": ("name", "value"), "organizations": ("name", "value")}
NORMALIZED_TABLE_COLUMNS = {
    "tags": ("tag", "normalized_tag", "compact_tag"),
    "people": ("name", "normalized_name", "compact_name"),
    "organizations": ("name", "normalized_name", "compact_name"),
}

__all__ = [
    "DOCUMENT_COLUMNS",
    "JsonDict",
    "LoadedBundle",
    "NORMALIZED_LIST_KEYS",
    "NORMALIZED_TABLE_COLUMNS",
    "PreparedBundle",
    "ProvenanceMap",
]
