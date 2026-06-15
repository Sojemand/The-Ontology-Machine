"""Path-stable embedding repository API."""

from __future__ import annotations

from .search_repository import (
    fetch_chunk_search_candidates,
    fetch_document_search_candidates,
    fetch_search_candidates,
)
from .source_repository import fetch_pending_embedding_sources
from .storage_repository import (
    checkpoint_wal,
    clear_embedding_chunks,
    load_embedding,
    store_embedding,
    store_embedding_chunk,
)

__all__ = [
    "checkpoint_wal",
    "clear_embedding_chunks",
    "fetch_chunk_search_candidates",
    "fetch_document_search_candidates",
    "fetch_pending_embedding_sources",
    "fetch_search_candidates",
    "load_embedding",
    "store_embedding",
    "store_embedding_chunk",
]
