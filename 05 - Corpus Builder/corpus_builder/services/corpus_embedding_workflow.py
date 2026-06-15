"""Embedding service workflow."""

from __future__ import annotations

from pathlib import Path

from ..context import ModuleContext
from ..database import connect, ensure_schema
from ..embeddings import embed_pending_result, resolve_runtime_capability
from ..models.results import EmbeddingRunResult
from ..models.types import EmbeddingRequest
from .config import load_module_config, resolve_corpus_db_path


def generate_embeddings(context: ModuleContext, request: EmbeddingRequest) -> EmbeddingRunResult:
    config = load_module_config(context)
    capability = resolve_runtime_capability()
    if capability.status != "available":
        return EmbeddingRunResult(status="disabled", count=0, reason=capability.reason)

    db_path = resolve_corpus_db_path(context, request.corpus_db_path, config=config)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        ensure_schema(conn)
        return embed_pending_result(
            conn,
            config.embeddings,
            request.runtime_settings,
            api_key=capability.api_key,
        )
    finally:
        conn.close()
