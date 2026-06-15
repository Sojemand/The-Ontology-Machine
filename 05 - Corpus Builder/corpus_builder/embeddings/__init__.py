"""Path-stable surface for Corpus Builder embedding helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..models.types import EmbeddingConfig, EmbeddingRuntimeSettings
from . import adapter as _adapter
from . import domain as _domain
from . import repository as _repository
from . import workflow as _workflow
from .types import RuntimeEmbeddingsCapability


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return _domain.cosine_similarity(a, b)


def build_embedding_text(document: dict[str, Any], max_chars: int = 12000) -> str:
    return _domain.build_embedding_text(document, max_chars=max_chars)


def store_embedding(
    conn: sqlite3.Connection,
    doc_id: str,
    text: str,
    vector: list[float],
    model: str,
) -> None:
    _repository.store_embedding(conn, doc_id, text, vector, model)


def store_embedding_chunk(
    conn: sqlite3.Connection,
    item,
    vector: list[float],
    model: str,
) -> None:
    _repository.store_embedding_chunk(conn, item, vector, model)


def load_embedding(
    vector_blob: bytes,
    *,
    expected_dimensions: int | None = None,
) -> list[float]:
    return _repository.load_embedding(
        vector_blob,
        expected_dimensions=expected_dimensions,
    )


def get_embeddings(
    texts: list[str],
    model: str,
    api_key: str | None = None,
    *,
    base_url: str | None = None,
    provider_family: str | None = None,
) -> list[list[float]]:
    return _adapter.get_embeddings(texts, model=model, api_key=api_key, base_url=base_url, provider_family=provider_family)


def check_api_available(
    api_key: str | None,
    *,
    model: str,
    base_url: str | None = None,
    provider_family: str | None = None,
) -> tuple[bool, str]:
    return _adapter.check_api_available(api_key, model=model, base_url=base_url, provider_family=provider_family)


def resolve_runtime_capability() -> RuntimeEmbeddingsCapability:
    return _adapter.resolve_runtime_capability()


def sanitize_reason(text: str) -> str:
    return _adapter.sanitize_reason(text)


def get_embeddings_for_runtime(
    texts: list[str],
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    provider_family: str | None = None,
) -> list[list[float]]:
    return _adapter.get_embeddings_for_runtime(
        texts,
        runtime_settings,
        api_key=api_key,
        base_url=base_url,
        provider_family=provider_family,
        api_client=get_embeddings,
    )


def cosine_search(
    conn: sqlite3.Connection,
    query_vector: list[float],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    return _workflow.cosine_search(
        conn,
        query_vector,
        top_k=top_k,
        load_embedding_fn=load_embedding,
        cosine_similarity_fn=cosine_similarity,
    )


def embed_document(
    conn: sqlite3.Connection,
    doc_id: str,
    structured_json: dict[str, Any],
    config: EmbeddingConfig,
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None = None,
) -> bool:
    return _workflow.embed_document(
        conn,
        doc_id,
        structured_json,
        config,
        runtime_settings,
        api_key=api_key,
        build_embedding_text_fn=build_embedding_text,
        get_embeddings_for_runtime_fn=get_embeddings_for_runtime,
        store_embedding_fn=store_embedding,
        store_embedding_chunk_fn=store_embedding_chunk,
    )


def embed_pending_result(
    conn: sqlite3.Connection,
    config: EmbeddingConfig,
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None = None,
):
    return _workflow.embed_pending_result(
        conn,
        config,
        runtime_settings,
        api_key=api_key,
        build_embedding_text_fn=build_embedding_text,
        get_embeddings_for_runtime_fn=get_embeddings_for_runtime,
        store_embedding_fn=store_embedding,
        store_embedding_chunk_fn=store_embedding_chunk,
    )


def embed_pending(
    conn: sqlite3.Connection,
    config: EmbeddingConfig,
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None = None,
) -> int:
    return _workflow.embed_pending(
        conn,
        config,
        runtime_settings,
        api_key=api_key,
        build_embedding_text_fn=build_embedding_text,
        get_embeddings_for_runtime_fn=get_embeddings_for_runtime,
        store_embedding_fn=store_embedding,
        store_embedding_chunk_fn=store_embedding_chunk,
    )


__all__ = [
    "build_embedding_text",
    "check_api_available",
    "cosine_search",
    "cosine_similarity",
    "embed_document",
    "embed_pending",
    "embed_pending_result",
    "get_embeddings",
    "get_embeddings_for_runtime",
    "load_embedding",
    "resolve_runtime_capability",
    "sanitize_reason",
    "store_embedding",
    "store_embedding_chunk",
]
