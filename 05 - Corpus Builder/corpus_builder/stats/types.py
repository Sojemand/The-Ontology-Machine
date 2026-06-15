"""Named contracts for corpus stats stages."""

from __future__ import annotations

from typing import TypedDict


class CorpusDateRange(TypedDict):
    earliest: str | None
    latest: str | None


class CorpusStats(TypedDict):
    total_documents: int
    total_archived: int
    total_fields: int
    total_relations: int
    total_entities: int
    stale_documents: int
    has_embeddings: bool
    embeddings_count: int
    by_document_type: dict[str, int]
    by_category: dict[str, int]
    by_language: dict[str, int]
    by_validator_status: dict[str, int]
    by_promotion_slot: dict[str, int]
    by_projection: dict[str, int]
    by_materialization_state: dict[str, int]
    by_entity_type: dict[str, int]
    top_tags: list[tuple[str, int]]
    top_people: list[tuple[str, int]]
    top_organizations: list[tuple[str, int]]
    top_field_keys: list[tuple[str, int]]
    top_promotion_values: list[tuple[str, int]]
    avg_confidence: float | None
    avg_fields_per_doc: float | None
    promotion_numeric_totals: dict[str, float]
    date_range: CorpusDateRange
