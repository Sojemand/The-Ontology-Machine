"""Workflow stage for embedding generation and vector search."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Callable

from ..models.results import EmbeddingRunResult
from ..models.types import EmbeddingConfig, EmbeddingRuntimeSettings
from . import adapter, domain, policy, repository
from .run_helpers import build_items_for_source, embedding_run_reason, fetch_vectors_for_items, store_items
from .search_workflow import cosine_search
from .types import EmbeddingBatchItem

logger = logging.getLogger(__name__)


def embed_document(
    conn: sqlite3.Connection,
    doc_id: str,
    structured_json: dict[str, Any],
    config: EmbeddingConfig,
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None = None,
    build_embedding_text_fn: Callable[[dict[str, Any], int], str],
    get_embeddings_for_runtime_fn: Callable[..., list[list[float]]],
    store_embedding_fn: Callable[[sqlite3.Connection, str, str, list[float], str], None],
    store_embedding_chunk_fn: Callable[[sqlite3.Connection, EmbeddingBatchItem, list[float], str], None],
) -> bool:
    source = domain.build_inline_source(doc_id, structured_json)
    items = build_items_for_source(source, config, build_embedding_text_fn)
    if not items:
        logger.warning("Kein Embedding-Text fuer %s", doc_id)
        return False

    vectors, error = fetch_vectors_for_items(
        items,
        config,
        runtime_settings,
        api_key=api_key,
        get_embeddings_for_runtime_fn=get_embeddings_for_runtime_fn,
    )
    if error:
        return False

    stored, _error = store_items(
        conn,
        source,
        items,
        vectors,
        model_name=policy.runtime_model_name(runtime_settings),
        store_embedding_fn=store_embedding_fn,
        store_embedding_chunk_fn=store_embedding_chunk_fn,
    )
    return stored


def embed_pending(
    conn: sqlite3.Connection,
    config: EmbeddingConfig,
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None = None,
    build_embedding_text_fn: Callable[[dict[str, Any], int], str],
    get_embeddings_for_runtime_fn: Callable[..., list[list[float]]],
    store_embedding_fn: Callable[[sqlite3.Connection, str, str, list[float], str], None],
    store_embedding_chunk_fn: Callable[[sqlite3.Connection, EmbeddingBatchItem, list[float], str], None],
) -> int:
    return embed_pending_result(
        conn,
        config,
        runtime_settings,
        api_key=api_key,
        build_embedding_text_fn=build_embedding_text_fn,
        get_embeddings_for_runtime_fn=get_embeddings_for_runtime_fn,
        store_embedding_fn=store_embedding_fn,
        store_embedding_chunk_fn=store_embedding_chunk_fn,
    ).count


def embed_pending_result(
    conn: sqlite3.Connection,
    config: EmbeddingConfig,
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None = None,
    build_embedding_text_fn: Callable[[dict[str, Any], int], str],
    get_embeddings_for_runtime_fn: Callable[..., list[list[float]]],
    store_embedding_fn: Callable[[sqlite3.Connection, str, str, list[float], str], None],
    store_embedding_chunk_fn: Callable[[sqlite3.Connection, EmbeddingBatchItem, list[float], str], None],
) -> EmbeddingRunResult:
    resolved_api_key = _resolve_api_key(api_key)
    if resolved_api_key is None:
        capability = adapter.resolve_runtime_capability()
        if capability.status != "available":
            logger.info("Keine Embeddings-API verfuegbar - Embeddings uebersprungen")
            return EmbeddingRunResult(status="disabled", count=0, reason=capability.reason)
        resolved_api_key = capability.api_key

    sources = repository.fetch_pending_embedding_sources(conn)
    if not sources:
        logger.info("Alle Dokumente haben bereits Embeddings")
        return EmbeddingRunResult(status="completed", count=0, reason="Keine neuen Embeddings notwendig.")

    vector_count = 0
    document_count = 0
    chunk_count = 0
    model_name = policy.runtime_model_name(runtime_settings)
    for source in sources:
        items = build_items_for_source(source, config, build_embedding_text_fn)
        if not items:
            continue
        vectors, error = fetch_vectors_for_items(
            items,
            config,
            runtime_settings,
            api_key=resolved_api_key,
            get_embeddings_for_runtime_fn=get_embeddings_for_runtime_fn,
        )
        if error:
            return EmbeddingRunResult(status="error", count=vector_count, reason=error)
        stored, store_error = store_items(
            conn,
            source,
            items,
            vectors,
            model_name=model_name,
            store_embedding_fn=store_embedding_fn,
            store_embedding_chunk_fn=store_embedding_chunk_fn,
        )
        if not stored:
            return EmbeddingRunResult(status="error", count=vector_count, reason=store_error)
        vector_count += len(items)
        document_count += 1
        chunk_count += sum(1 for item in items if item.target_kind == "chunk")
    return EmbeddingRunResult(
        status="completed",
        count=vector_count,
        reason=embedding_run_reason(vector_count, document_count=document_count, chunk_count=chunk_count),
    )


def _resolve_api_key(api_key: str | None) -> str | None:
    return str(api_key or "").strip() or None
