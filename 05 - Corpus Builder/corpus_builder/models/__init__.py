"""Path-stable surface for Corpus Builder config, results, and serialization."""

from __future__ import annotations

from .config import load_config
from .results import (
    EmbeddingRunResult,
    ExportResult,
    LoadBatchResult,
    LoadResult,
    SearchResult,
)
from .serialization import atomic_bytes_write, atomic_file_write, atomic_json_write, atomic_text_write, now_iso
from .types import (
    ArchiveConfig,
    CorpusConfig,
    DatabaseConfig,
    EmbeddingConfig,
    EmbeddingRequest,
    EmbeddingRuntimeSettings,
    FTSConfig,
    LoadBundle,
    SemanticConfig,
    SourceConfig,
)

__all__ = [
    "ArchiveConfig",
    "CorpusConfig",
    "DatabaseConfig",
    "EmbeddingConfig",
    "EmbeddingRequest",
    "EmbeddingRuntimeSettings",
    "EmbeddingRunResult",
    "ExportResult",
    "FTSConfig",
    "LoadBatchResult",
    "LoadBundle",
    "LoadResult",
    "SearchResult",
    "SemanticConfig",
    "SourceConfig",
    "atomic_bytes_write",
    "atomic_file_write",
    "atomic_json_write",
    "atomic_text_write",
    "load_config",
    "now_iso",
]
