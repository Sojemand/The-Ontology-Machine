"""Path-stable corpus DB service workflow API."""

from __future__ import annotations

from ..embeddings import embed_pending_result, resolve_runtime_capability
from ..search import fulltext_search, hybrid_search, semantic_search
from ..search.policy_store import load_search_policy
from .config import resolve_corpus_db_path
from . import corpus_embedding_workflow as _embedding
from . import corpus_load_workflow as _load
from . import corpus_read_workflow as _read
from .corpus_read_workflow import _open_readonly_connection


def load_batch(*args, **kwargs):
    return _load.load_batch(*args, **kwargs)


def generate_embeddings(*args, **kwargs):
    _embedding.embed_pending_result = embed_pending_result
    _embedding.resolve_runtime_capability = resolve_runtime_capability
    _embedding.resolve_corpus_db_path = resolve_corpus_db_path
    return _embedding.generate_embeddings(*args, **kwargs)


def search_corpus(*args, **kwargs):
    _read.fulltext_search = fulltext_search
    _read.hybrid_search = hybrid_search
    _read.load_search_policy = load_search_policy
    _read.resolve_corpus_db_path = resolve_corpus_db_path
    _read.resolve_runtime_capability = resolve_runtime_capability
    _read.semantic_search = semantic_search
    _read._open_readonly_connection = _open_readonly_connection
    return _read.search_corpus(*args, **kwargs)


def export_corpus(*args, **kwargs):
    _read.resolve_corpus_db_path = resolve_corpus_db_path
    _read._open_readonly_connection = _open_readonly_connection
    return _read.export_corpus(*args, **kwargs)


def get_stats(*args, **kwargs):
    _read.resolve_corpus_db_path = resolve_corpus_db_path
    _read._open_readonly_connection = _open_readonly_connection
    return _read.get_stats(*args, **kwargs)


def list_archived(*args, **kwargs):
    _read.resolve_corpus_db_path = resolve_corpus_db_path
    _read._open_readonly_connection = _open_readonly_connection
    return _read.list_archived(*args, **kwargs)


__all__ = [
    "_open_readonly_connection",
    "embed_pending_result",
    "export_corpus",
    "fulltext_search",
    "generate_embeddings",
    "get_stats",
    "hybrid_search",
    "list_archived",
    "load_batch",
    "load_search_policy",
    "resolve_corpus_db_path",
    "resolve_runtime_capability",
    "search_corpus",
    "semantic_search",
]
