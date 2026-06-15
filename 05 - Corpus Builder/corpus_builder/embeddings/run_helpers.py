"""Batch helpers for embedding generation runs."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Callable

from ..models.types import EmbeddingConfig, EmbeddingRuntimeSettings
from . import adapter, domain, policy, repository, validation
from .types import EmbeddingBatchItem, PendingEmbeddingSource

logger = logging.getLogger(__name__)


def build_items_for_source(
    source: PendingEmbeddingSource,
    config: EmbeddingConfig,
    build_embedding_text_fn: Callable[[dict[str, Any], int], str],
) -> list[EmbeddingBatchItem]:
    items: list[EmbeddingBatchItem] = []
    summary_text = _build_text_for_source(source, config, build_embedding_text_fn)
    if summary_text.strip():
        items.append(EmbeddingBatchItem(document_id=source.document_id, text=summary_text))
    for chunk in domain.build_embedding_chunks(source, policy.config_max_text_chars(config)):
        items.append(
            EmbeddingBatchItem(
                document_id=chunk.document_id,
                text=chunk.text,
                target_kind="chunk",
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                chunk_type=chunk.chunk_type,
                page=chunk.page,
                source_kind=chunk.source_kind,
                source_refs_json=chunk.source_refs_json,
            )
        )
    return items


def fetch_vectors_for_items(
    items: list[EmbeddingBatchItem],
    config: EmbeddingConfig,
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None,
    get_embeddings_for_runtime_fn: Callable[..., list[list[float]]],
) -> tuple[list[list[float]], str | None]:
    if not items:
        return [], None

    batch_size = policy.config_batch_size(config)
    expected_dimensions = policy.config_expected_dimensions(config)
    vectors: list[list[float]] = []
    try:
        for offset in range(0, len(items), batch_size):
            batch = items[offset : offset + batch_size]
            batch_vectors = get_embeddings_for_runtime_fn(
                [item.text for item in batch],
                runtime_settings,
                api_key=api_key,
            )
            validation.validate_vectors(
                batch_vectors,
                expected_count=len(batch),
                expected_dimensions=expected_dimensions,
            )
            vectors.extend([list(vector) for vector in batch_vectors])
    except Exception as exc:
        logger.error("Embedding-Erzeugung fehlgeschlagen: %s", exc)
        return [], adapter.sanitize_reason(str(exc))
    return vectors, None


def store_items(
    conn: sqlite3.Connection,
    source: PendingEmbeddingSource,
    items: list[EmbeddingBatchItem],
    vectors: list[list[float]],
    *,
    model_name: str,
    store_embedding_fn: Callable[[sqlite3.Connection, str, str, list[float], str], None],
    store_embedding_chunk_fn: Callable[[sqlite3.Connection, EmbeddingBatchItem, list[float], str], None],
) -> tuple[bool, str | None]:
    try:
        with conn:
            if any(item.target_kind == "chunk" for item in items):
                repository.clear_embedding_chunks(conn, source.document_id)
            for item, vector in zip(items, vectors):
                if item.target_kind == "chunk":
                    store_embedding_chunk_fn(conn, item, vector, model_name)
                else:
                    store_embedding_fn(conn, item.document_id, item.text, vector, model_name)
        repository.checkpoint_wal(conn)
        return True, None
    except Exception as exc:
        if conn.in_transaction:
            conn.rollback()
        logger.error("Embedding-Speicherung fehlgeschlagen fuer %s: %s", source.document_id, exc)
        return False, adapter.sanitize_reason(str(exc))


def embedding_run_reason(vector_count: int, *, document_count: int, chunk_count: int) -> str:
    if vector_count <= 0:
        return "Keine neuen Embeddings notwendig."
    noun = "Embedding" if vector_count == 1 else "Embeddings"
    summary_noun = "Dokument-Summary" if document_count == 1 else "Dokument-Summaries"
    chunk_noun = "Chunk" if chunk_count == 1 else "Chunks"
    return f"{vector_count} {noun} erzeugt ({document_count} {summary_noun}, {chunk_count} {chunk_noun})."


def _build_text_for_source(
    source: PendingEmbeddingSource,
    config: EmbeddingConfig,
    build_embedding_text_fn: Callable[[dict[str, Any], int], str],
) -> str:
    document, error = domain.parse_document_json(source.normalized_json)
    if error == "invalid_json":
        logger.warning("normalized_json fuer %s ist ungueltig", source.document_id)
        return ""
    if error == "not_object":
        logger.warning("normalized_json fuer %s ist kein JSON-Objekt", source.document_id)
        return ""
    if document is None:
        return ""
    if source.promotions:
        document = dict(document)
        document["document_promotions"] = [
            {
                "promotion_id": promotion.promotion_id,
                "slot": promotion.slot,
                "slot_label": promotion.slot_label,
                "value_type": promotion.value_type,
                "query_role": promotion.query_role,
                "display_value": promotion.display_value,
                "source_path": promotion.source_path,
            }
            for promotion in source.promotions
        ]
    return build_embedding_text_fn(document, policy.config_max_text_chars(config))
