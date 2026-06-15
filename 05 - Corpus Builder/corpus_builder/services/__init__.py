"""Path-stable surface for Corpus Builder service workflows."""

from __future__ import annotations

from .bundle_adapter import build_load_bundle
from .config import load_module_config, resolve_corpus_db_path
from .corpus_workflow import (
    export_corpus,
    generate_embeddings,
    get_stats,
    list_archived,
    load_batch,
    search_corpus,
)
from .corpus_context import activate_corpus_context, create_empty_corpus_db
from .corpus_admin import reset_active_corpus_db
from .ontology_workflow import run_basic_relation_mining
from .semantic_workflow import (
    activation_preflight,
    apply_semantic_release,
    audit_semantics,
    backfill_semantics,
    create_and_activate_new_corpus_db,
    create_and_rebuild_new_corpus_db,
    load_semantic_release,
    merge_corpus_databases,
    merge_preflight,
    read_active_semantic_release,
    resolve_existing_corpus_db_path,
    semantic_status,
)

__all__ = [
    "activation_preflight",
    "activate_corpus_context",
    "apply_semantic_release",
    "audit_semantics",
    "backfill_semantics",
    "build_load_bundle",
    "create_and_activate_new_corpus_db",
    "create_empty_corpus_db",
    "reset_active_corpus_db",
    "run_basic_relation_mining",
    "create_and_rebuild_new_corpus_db",
    "export_corpus",
    "generate_embeddings",
    "get_stats",
    "list_archived",
    "load_batch",
    "load_module_config",
    "load_semantic_release",
    "merge_corpus_databases",
    "merge_preflight",
    "read_active_semantic_release",
    "resolve_corpus_db_path",
    "resolve_existing_corpus_db_path",
    "search_corpus",
    "semantic_status",
]
