"""Embedding chunk shaping from normalized payloads and evidence sources."""

from __future__ import annotations

from typing import Any

from .chunk_sources import (
    content_free_text,
    decode_row_json,
    inline_field_sources,
    inline_row_sources,
    page_from_file_path,
    page_from_row_source,
)
from .chunk_text import finalize_chunk_drafts, pack_text_units, split_free_text_chunks
from .common import as_optional_int, chunk_char_cap, clean_text, first_non_empty, row_text
from .math_domain import parse_document_json
from .types import EmbeddingChunkDraft, PendingEmbeddingSource


def build_embedding_chunks(source: PendingEmbeddingSource, max_chars: int = 12000) -> list[EmbeddingChunkDraft]:
    document, error = parse_document_json(source.normalized_json)
    if error in {"invalid_json", "not_object"} or document is None:
        document = {}
    chunk_cap = chunk_char_cap(max_chars)
    drafts: list[dict[str, Any]] = []
    drafts.extend(_build_promotion_chunks(source, max_chars=chunk_cap))
    drafts.extend(_content_chunks(source, document, max_chars=chunk_cap))
    drafts.extend(_build_row_chunks(source, document, max_chars=chunk_cap))
    drafts.extend(_build_field_chunks(source, document, max_chars=chunk_cap))
    return finalize_chunk_drafts(source.document_id, drafts)


def _build_promotion_chunks(source: PendingEmbeddingSource, *, max_chars: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for promotion in source.promotions:
        label = promotion.slot_label or promotion.slot
        role = f" ({promotion.query_role})" if promotion.query_role else ""
        text = clean_text(f"{label}{role}: {promotion.display_value}")
        if not text:
            continue
        items.append(
            {
                "text": text,
                "page": page_from_file_path(source.file_path),
                "refs": [promotion.promotion_id if promotion.promotion_id is not None else promotion.source_path or promotion.slot],
            }
        )
    return pack_text_units(source, chunk_type="promotion", source_kind="document_promotions", items=items, max_chars=max_chars)


def _content_chunks(source: PendingEmbeddingSource, document: dict[str, Any], *, max_chars: int) -> list[dict[str, Any]]:
    segment_atoms = [atom for atom in source.evidence_atoms if atom.atom_type == "segment" and clean_text(atom.text_value)]
    if segment_atoms:
        return pack_text_units(
            source,
            chunk_type="segment",
            source_kind="evidence_atoms",
            items=[{"text": str(atom.text_value or ""), "page": atom.page, "refs": [atom.atom_id]} for atom in segment_atoms],
            max_chars=max_chars,
        )
    free_text_atoms = [atom for atom in source.evidence_atoms if atom.atom_type == "free_text" and clean_text(atom.text_value)]
    if free_text_atoms:
        chunks: list[dict[str, Any]] = []
        for atom in free_text_atoms:
            chunks.extend(
                split_free_text_chunks(
                    source,
                    text=str(atom.text_value or ""),
                    chunk_type="free_text",
                    source_kind="evidence_atoms",
                    source_refs=[atom.atom_id],
                    page=atom.page,
                    max_chars=max_chars,
                )
            )
        return chunks
    free_text = first_non_empty(source.payload_free_text, content_free_text(document))
    if not free_text:
        return []
    return split_free_text_chunks(
        source,
        text=free_text,
        chunk_type="free_text",
        source_kind="document_payloads",
        source_refs=["content.free_text"],
        page=page_from_file_path(source.file_path),
        max_chars=max_chars,
    )


def _build_row_chunks(source: PendingEmbeddingSource, document: dict[str, Any], *, max_chars: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row_source in list(source.rows) or inline_row_sources(document):
        row = decode_row_json(row_source.row_json)
        if not row:
            continue
        text = clean_text(row_text(row))
        if text:
            items.append(
                {
                    "text": f"Zeile {row_source.row_index + 1}: {text}",
                    "page": page_from_row_source(row_source, source.file_path),
                    "refs": [row_source.row_id if row_source.row_id is not None else row_source.source_ref or f"content.rows[{row_source.row_index}]"],
                }
            )
    return pack_text_units(source, chunk_type="row", source_kind="extracted_rows", items=items, max_chars=max_chars)


def _build_field_chunks(source: PendingEmbeddingSource, document: dict[str, Any], *, max_chars: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for field_source in list(source.fields) or inline_field_sources(document):
        line = clean_text(f"{field_source.key}: {field_source.value}")
        if line:
            items.append(
                {
                    "text": line,
                    "page": page_from_file_path(source.file_path),
                    "refs": [field_source.field_id if field_source.field_id is not None else field_source.source_ref or f"content.fields.{field_source.key}"],
                }
            )
    return pack_text_units(source, chunk_type="field", source_kind="extracted_fields", items=items, max_chars=max_chars)
