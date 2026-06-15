"""Config-stage helpers for the Corpus Builder services surface."""

from __future__ import annotations

from pathlib import Path

from ..context import ModuleContext
from ..models.config import load_config
from ..models.types import CorpusConfig


def load_module_config(context: ModuleContext) -> CorpusConfig:
    return load_config(context.config_path, module_root=context.module_root)


def resolve_corpus_db_path(
    context: ModuleContext,
    corpus_db_path: str | Path | None = None,
    *,
    config: CorpusConfig | None = None,
) -> str:
    if corpus_db_path is not None and str(corpus_db_path).strip():
        return str(context.resolve_path(corpus_db_path))
    resolved_config = config or load_module_config(context)
    raw_value = resolved_config.database.corpus_db
    return str(context.resolve_path(raw_value))
