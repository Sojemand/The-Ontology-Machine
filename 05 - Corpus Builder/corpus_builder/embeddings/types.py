"""Named carriers for embedding workflow boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class EvidenceAtomSource:
    atom_id: int
    atom_type: str
    page: int | None
    json_path: str
    source_ref: str | None = None
    text_value: str | None = None
    context_label: str | None = None
    context_window: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractedRowSource:
    row_id: int | None
    row_index: int
    row_json: str
    source_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractedFieldSource:
    field_id: int | None
    key: str
    value: str
    normalized_value: str | None = None
    source_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PromotionSource:
    promotion_id: int | None
    slot: str
    slot_label: str | None
    value_type: str | None
    query_role: str | None
    display_value: str
    source_path: str | None = None


@dataclass(frozen=True, slots=True)
class PendingEmbeddingSource:
    document_id: str
    normalized_json: str
    file_name: str | None = None
    file_path: str | None = None
    document_type: str | None = None
    page_count: int | None = None
    payload_free_text: str | None = None
    evidence_atoms: tuple[EvidenceAtomSource, ...] = ()
    promotions: tuple[PromotionSource, ...] = ()
    rows: tuple[ExtractedRowSource, ...] = ()
    fields: tuple[ExtractedFieldSource, ...] = ()


@dataclass(frozen=True, slots=True)
class EmbeddingChunkDraft:
    chunk_id: str
    document_id: str
    chunk_index: int
    chunk_type: str
    page: int | None
    source_kind: str
    source_refs_json: str
    text: str


@dataclass(frozen=True, slots=True)
class EmbeddingBatchItem:
    document_id: str
    text: str
    target_kind: Literal["document", "chunk"] = "document"
    chunk_id: str | None = None
    chunk_index: int | None = None
    chunk_type: str | None = None
    page: int | None = None
    source_kind: str | None = None
    source_refs_json: str | None = None


@dataclass(frozen=True, slots=True)
class SearchCandidate:
    document_id: str
    title: str | None
    description: str | None
    vector_blob: bytes
    dimensions: int
    snippet: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeEmbeddingsCapability:
    status: Literal["available", "unavailable"]
    api_key: str | None = None
    provider_id: str = ""
    provider_family: str = ""
    base_url: str = ""
    reason: str = ""
