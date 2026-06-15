"""Workflow stage for fulltext, semantic, hybrid, and readonly query flows."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from ..models.results import SearchResult
from ..models.types import EmbeddingRuntimeSettings
from .policy_store import load_search_policy, readonly_max_rows
from . import domain, policy, repository, validation

logger = logging.getLogger(__name__)


def has_embeddings(conn: sqlite3.Connection) -> bool:
    return repository.has_embeddings(conn)


def fulltext_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
    filters: dict[str, object] | None = None,
) -> list[SearchResult]:
    limit = policy.normalize_positive_int(limit, fallback=20)

    try:
        rows = repository.search_fulltext_rows(
            conn,
            query,
            validation.validate_filters(filters),
            limit=limit,
        )
    except sqlite3.Error as exc:
        logger.error("FTS-Suche fehlgeschlagen: %s", exc)
        return []
    return [domain.build_fts_result(row) for row in rows]


def semantic_search(
    conn: sqlite3.Connection,
    query: str,
    top_k: int = 10,
    runtime_settings: EmbeddingRuntimeSettings | None = None,
    api_key: str | None = None,
) -> list[SearchResult]:
    from ..embeddings import cosine_search, get_embeddings_for_runtime, resolve_runtime_capability

    top_k = policy.normalize_positive_int(top_k, fallback=10)
    if not repository.has_embeddings(conn):
        logger.warning("Keine Embeddings vorhanden - semantische Suche nicht moeglich")
        return []
    if runtime_settings is None:
        raise ValueError("runtime_settings.model fehlt oder ist ungueltig.")

    resolved_api_key = str(api_key or "").strip() or None
    if resolved_api_key is None:
        capability = resolve_runtime_capability()
        if capability.status != "available":
            raise RuntimeError(capability.reason)
        resolved_api_key = capability.api_key

    try:
        query_embedding = get_embeddings_for_runtime([query], runtime_settings, api_key=resolved_api_key)[0]
    except Exception as exc:
        logger.error("Embedding-Erzeugung fehlgeschlagen: %s", exc)
        return []

    return [
        domain.build_vector_result(hit)
        for hit in cosine_search(conn, query_embedding, top_k=top_k)
    ]


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    top_k: int = 10,
    filters: dict[str, object] | None = None,
    fts_weight: float = 0.6,
    vec_weight: float = 0.4,
    candidate_multiplier: int = 2,
    normalize_fts_scores: bool = True,
    runtime_settings: EmbeddingRuntimeSettings | None = None,
    api_key: str | None = None,
) -> list[SearchResult]:
    top_k = policy.normalize_positive_int(top_k, fallback=10)
    candidate_limit = policy.hybrid_candidate_limit(
        top_k,
        candidate_multiplier=candidate_multiplier,
    )
    fts_results = fulltext_search(
        conn,
        query,
        limit=candidate_limit,
        filters=filters,
    )

    vector_results: list[SearchResult] = []
    if repository.has_embeddings(conn):
        vector_results = semantic_search(
            conn,
            query,
            top_k=candidate_limit,
            runtime_settings=runtime_settings,
            api_key=api_key,
        )

    return domain.merge_hybrid_results(
        fts_results,
        vector_results,
        fts_weight=fts_weight,
        vec_weight=vec_weight,
        top_k=top_k,
        normalize_fts_scores=normalize_fts_scores,
    )


def safe_query(
    conn: sqlite3.Connection,
    sql: str,
    params: Sequence[object] | None = None,
    max_rows: int | None = None,
    module_root: str | Path | None = None,
) -> list[dict]:
    max_rows = _resolved_max_rows(max_rows, module_root=module_root)
    prepared = validation.validate_readonly_query(sql)
    return repository.execute_readonly_query(conn, prepared, params, max_rows=max_rows)


def _resolved_max_rows(max_rows: int | None, *, module_root: str | Path | None) -> int:
    if max_rows is not None:
        return policy.normalize_positive_int(max_rows, fallback=100)
    if module_root is None:
        return 100
    return readonly_max_rows(load_search_policy(module_root))
