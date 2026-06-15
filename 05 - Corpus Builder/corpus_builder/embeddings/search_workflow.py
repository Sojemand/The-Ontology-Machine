"""Vector search workflow helpers."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Callable

from . import policy, repository
from .types import SearchCandidate

logger = logging.getLogger(__name__)


def cosine_search(
    conn: sqlite3.Connection,
    query_vector: list[float],
    *,
    top_k: int = 10,
    load_embedding_fn: Callable[..., list[float]],
    cosine_similarity_fn: Callable[[list[float], list[float]], float],
) -> list[dict[str, Any]]:
    top_k = policy.normalize_positive_int(top_k, fallback=10)
    chunk_candidates = repository.fetch_chunk_search_candidates(conn)
    if chunk_candidates:
        return _rank_candidates(
            chunk_candidates,
            query_vector,
            load_embedding_fn=load_embedding_fn,
            cosine_similarity_fn=cosine_similarity_fn,
        )[:top_k]
    return _rank_candidates(
        repository.fetch_document_search_candidates(conn),
        query_vector,
        load_embedding_fn=load_embedding_fn,
        cosine_similarity_fn=cosine_similarity_fn,
    )[:top_k]


def _rank_candidates(
    candidates: list[SearchCandidate],
    query_vector: list[float],
    *,
    load_embedding_fn: Callable[..., list[float]],
    cosine_similarity_fn: Callable[[list[float], list[float]], float],
) -> list[dict[str, Any]]:
    skipped = 0
    best_by_document: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if candidate.dimensions != len(query_vector):
            skipped += 1
            continue
        try:
            vector = load_embedding_fn(
                candidate.vector_blob,
                expected_dimensions=candidate.dimensions,
            )
        except ValueError as exc:
            logger.warning("Defektes Embedding fuer %s uebersprungen: %s", candidate.document_id, exc)
            skipped += 1
            continue
        similarity = cosine_similarity_fn(query_vector, vector)
        current = best_by_document.get(candidate.document_id)
        if current is None or similarity > current["similarity"]:
            best_by_document[candidate.document_id] = {
                "document_id": candidate.document_id,
                "title": candidate.title,
                "description": candidate.description,
                "snippet": candidate.snippet,
                "similarity": similarity,
            }
    if skipped:
        logger.warning("%d inkompatible oder defekte Embeddings uebersprungen", skipped)
    ranked = list(best_by_document.values())
    ranked.sort(key=lambda item: item["similarity"], reverse=True)
    return ranked
