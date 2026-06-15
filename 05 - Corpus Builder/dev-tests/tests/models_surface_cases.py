from __future__ import annotations

from corpus_builder.models import (
    CorpusConfig,
    EmbeddingConfig,
    EmbeddingRequest,
    EmbeddingRuntimeSettings,
    EmbeddingRunResult,
    ExportResult,
    LoadBatchResult,
    LoadBundle,
    LoadResult,
    SearchResult,
    atomic_json_write,
    load_config,
    now_iso,
)


def test_models_surface_re_exports_split_package_contract():
    assert CorpusConfig.__module__ == "corpus_builder.models.types"
    assert EmbeddingConfig.__module__ == "corpus_builder.models.types"
    assert LoadBundle.__module__ == "corpus_builder.models.types"
    assert EmbeddingRequest.__module__ == "corpus_builder.models.types"
    assert EmbeddingRuntimeSettings.__module__ == "corpus_builder.models.types"
    assert LoadResult.__module__ == "corpus_builder.models.results"
    assert SearchResult.__module__ == "corpus_builder.models.results"
    assert ExportResult.__module__ == "corpus_builder.models.results"
    assert LoadBatchResult.__module__ == "corpus_builder.models.results"
    assert EmbeddingRunResult.__module__ == "corpus_builder.models.results"
    assert atomic_json_write.__module__ == "corpus_builder.models.serialization"
    assert load_config.__module__ == "corpus_builder.models.config"
    assert now_iso.__module__ == "corpus_builder.models.serialization"
