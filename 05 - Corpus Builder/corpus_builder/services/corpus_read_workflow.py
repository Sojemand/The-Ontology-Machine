"""Read-only corpus service workflows."""

from __future__ import annotations

from pathlib import Path

from ..context import ModuleContext
from ..database import connect, has_initialized_schema
from ..database.repository import list_archived_documents
from ..embeddings import resolve_runtime_capability
from ..export import export_csv, export_jsonl
from ..models.results import SearchResult
from ..models.types import EmbeddingRuntimeSettings
from ..search import fulltext_search, hybrid_search, semantic_search
from ..search.policy_store import (
    fulltext_limit_default,
    hybrid_candidate_multiplier,
    hybrid_top_k_default,
    hybrid_weights,
    load_search_policy,
    normalize_fts_by_max_score,
    semantic_top_k_default,
)
from ..stats import corpus_stats
from .config import resolve_corpus_db_path


def search_corpus(
    context: ModuleContext,
    *,
    corpus_db_path: str | Path | None,
    query: str,
    mode: str,
    limit: int | None,
    filters: dict[str, str] | None = None,
    runtime_settings: EmbeddingRuntimeSettings | None = None,
) -> list[SearchResult]:
    search_policy = load_search_policy(context.module_root)
    resolved_limit = _search_limit(mode, limit, search_policy)
    db_path = resolve_corpus_db_path(context, corpus_db_path)
    conn = _open_readonly_connection(db_path, action="search", require_fts=mode != "Semantisch")
    try:
        if mode in {"Hybrid", "Semantisch"}:
            return _vector_search(
                conn,
                query=query,
                mode=mode,
                top_k=resolved_limit,
                filters=filters,
                runtime_settings=runtime_settings,
                search_policy=search_policy,
            )
        return fulltext_search(
            conn,
            query,
            limit=resolved_limit,
            filters=filters or None,
        )
    finally:
        conn.close()


def export_corpus(
    context: ModuleContext,
    *,
    corpus_db_path: str | Path | None,
    output_path: str | Path,
    fmt: str,
    include_archived: bool,
):
    db_path = resolve_corpus_db_path(context, corpus_db_path)
    resolved_output = context.resolve_path(output_path)
    conn = _open_readonly_connection(db_path, action="export")
    try:
        if fmt == "jsonl":
            return export_jsonl(conn, resolved_output, include_archived=include_archived)
        return export_csv(conn, resolved_output, include_archived=include_archived)
    finally:
        conn.close()


def get_stats(context: ModuleContext, *, corpus_db_path: str | Path | None):
    db_path = resolve_corpus_db_path(context, corpus_db_path)
    conn = _open_readonly_connection(db_path, action="stats")
    try:
        return corpus_stats(conn)
    finally:
        conn.close()


def list_archived(context: ModuleContext, *, corpus_db_path: str | Path | None):
    db_path = resolve_corpus_db_path(context, corpus_db_path)
    conn = _open_readonly_connection(db_path, action="list_archived")
    try:
        return list_archived_documents(conn)
    finally:
        conn.close()


def _vector_search(
    conn,
    *,
    query: str,
    mode: str,
    top_k: int,
    filters: dict[str, str] | None,
    runtime_settings: EmbeddingRuntimeSettings | None,
    search_policy: dict[str, object],
) -> list[SearchResult]:
    capability = resolve_runtime_capability()
    if runtime_settings is None:
        raise ValueError("runtime_settings.model fehlt oder ist ungueltig.")
    if capability.status != "available":
        raise RuntimeError(capability.reason)
    if mode == "Semantisch":
        return semantic_search(conn, query, top_k=top_k, runtime_settings=runtime_settings, api_key=capability.api_key)
    return hybrid_search(
        conn,
        query,
        top_k=top_k,
        filters=filters or None,
        candidate_multiplier=hybrid_candidate_multiplier(search_policy),
        fts_weight=hybrid_weights(search_policy)[0],
        vec_weight=hybrid_weights(search_policy)[1],
        normalize_fts_scores=normalize_fts_by_max_score(search_policy),
        runtime_settings=runtime_settings,
        api_key=capability.api_key,
    )


def _search_limit(mode: str, limit: int | None, policy: dict[str, object]) -> int:
    if limit and limit > 0:
        return limit
    if mode == "Hybrid":
        return hybrid_top_k_default(policy)
    if mode == "Semantisch":
        return semantic_top_k_default(policy)
    return fulltext_limit_default(policy)


def _open_readonly_connection(db_path: str | Path, *, action: str, require_fts: bool = False):
    resolved_path = Path(db_path)
    if not resolved_path.exists():
        raise ValueError(_uninitialized_db_message(action, resolved_path))
    conn = connect(str(resolved_path))
    try:
        if not has_initialized_schema(conn, require_fts=require_fts):
            raise ValueError(_uninitialized_db_message(action, resolved_path))
        return conn
    except Exception:
        conn.close()
        raise


def _uninitialized_db_message(action: str, db_path: Path) -> str:
    return (
        f"corpus.db ist fuer {action} nicht initialisiert: {db_path}. "
        "Fuehre zuerst load, rebuild oder apply-release gegen eine initialisierte DB aus."
    )
