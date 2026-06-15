"""Text packing and finalization for embedding chunks."""

from __future__ import annotations

import json
from typing import Any

from .chunk_sources import split_long_text
from .common import CHUNK_LABELS, WHITESPACE_RE, as_optional_int, clean_text
from .types import EmbeddingChunkDraft, PendingEmbeddingSource


def pack_text_units(
    source: PendingEmbeddingSource,
    *,
    chunk_type: str,
    source_kind: str,
    items: list[dict[str, Any]],
    max_chars: int,
) -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = []
    bucket_lines: list[str] = []
    bucket_refs: list[object] = []
    bucket_page: int | None = None
    for item in items:
        raw_line = clean_text(item.get("text"))
        if not raw_line:
            continue
        item_page = as_optional_int(item.get("page"))
        refs = item.get("refs") or []
        for line in split_text_unit(source, chunk_type=chunk_type, text=raw_line, page=item_page, max_chars=max_chars):
            candidate_lines = [*bucket_lines, line]
            if bucket_lines and (
                item_page != bucket_page
                or len(compose_chunk_text(source, chunk_type, candidate_lines, page=bucket_page, max_chars=max_chars)) > max_chars
            ):
                drafts.append(make_chunk_draft(source, chunk_type=chunk_type, source_kind=source_kind, lines=bucket_lines, source_refs=bucket_refs, page=bucket_page, max_chars=max_chars))
                bucket_lines, bucket_refs, bucket_page = [], [], None
            if not bucket_lines:
                bucket_page = item_page
            bucket_lines.append(line)
            bucket_refs.extend(refs)
    if bucket_lines:
        drafts.append(make_chunk_draft(source, chunk_type=chunk_type, source_kind=source_kind, lines=bucket_lines, source_refs=bucket_refs, page=bucket_page, max_chars=max_chars))
    return [draft for draft in drafts if draft["text"]]


def split_free_text_chunks(
    source: PendingEmbeddingSource,
    *,
    text: str,
    chunk_type: str,
    source_kind: str,
    source_refs: list[object],
    page: int | None,
    max_chars: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for part in split_text_unit(source, chunk_type=chunk_type, text=text, page=page, max_chars=max_chars):
        draft = make_chunk_draft(
            source,
            chunk_type=chunk_type,
            source_kind=source_kind,
            lines=[part],
            source_refs=source_refs,
            page=page,
            max_chars=max_chars,
        )
        if draft["text"]:
            chunks.append(draft)
    return chunks


def split_text_unit(
    source: PendingEmbeddingSource,
    *,
    chunk_type: str,
    text: str,
    page: int | None,
    max_chars: int,
) -> list[str]:
    line = clean_text(text)
    if not line:
        return []
    if len(compose_chunk_text(source, chunk_type, [line], page=page, max_chars=max_chars)) <= max_chars:
        return [line]
    body_budget = max(1, max_chars - len(chunk_text_prefix(source, chunk_type, page=page)))
    return split_long_text(line, body_budget=body_budget)


def make_chunk_draft(
    source: PendingEmbeddingSource,
    *,
    chunk_type: str,
    source_kind: str,
    lines: list[str],
    source_refs: list[object],
    page: int | None,
    max_chars: int,
) -> dict[str, Any]:
    return {
        "chunk_type": chunk_type,
        "page": page,
        "source_kind": source_kind,
        "source_refs_json": json.dumps(list(dict.fromkeys(source_refs)), ensure_ascii=False),
        "text": compose_chunk_text(source, chunk_type, lines, page=page, max_chars=max_chars),
    }


def compose_chunk_text(source: PendingEmbeddingSource, chunk_type: str, lines: list[str], *, page: int | None, max_chars: int) -> str:
    body = "\n".join(line for line in lines if line)
    return f"{chunk_text_prefix(source, chunk_type, page=page)}{body}".strip()


def chunk_text_prefix(source: PendingEmbeddingSource, chunk_type: str, *, page: int | None) -> str:
    header = metadata_header(source, page=page)
    label = CHUNK_LABELS.get(chunk_type, "Inhalt")
    body_prefix = f"{label}:\n"
    if not header:
        return body_prefix
    return f"{header}\n\n{body_prefix}"


def metadata_header(source: PendingEmbeddingSource, *, page: int | None) -> str:
    parts: list[str] = []
    if source.document_type:
        parts.append(f"Typ: {source.document_type}")
    if source.file_name:
        parts.append(f"Datei: {source.file_name}")
    for promotion in source.promotions[:3]:
        label = promotion.slot_label or promotion.slot
        if promotion.query_role in {"title", "date"} and promotion.display_value != source.file_name:
            parts.append(f"{label}: {promotion.display_value}")
    if page is not None:
        parts.append(f"Seite: {page}")
    return " | ".join(parts)


def finalize_chunk_drafts(document_id: str, drafts: list[dict[str, Any]]) -> list[EmbeddingChunkDraft]:
    finalized: list[EmbeddingChunkDraft] = []
    seen: set[str] = set()
    for draft in drafts:
        text = clean_text(draft.get("text"))
        if not text:
            continue
        dedupe_key = WHITESPACE_RE.sub(" ", text).strip().lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        finalized.append(
            EmbeddingChunkDraft(
                chunk_id=f"{document_id}::chunk::{len(finalized):04d}",
                document_id=document_id,
                chunk_index=len(finalized),
                chunk_type=str(draft["chunk_type"]),
                page=as_optional_int(draft.get("page")),
                source_kind=str(draft["source_kind"]),
                source_refs_json=str(draft["source_refs_json"]),
                text=text,
            )
        )
    return finalized
