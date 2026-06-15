"""Path-stable re-export surface for semantic corpus workflows."""

from __future__ import annotations

from .corpus_db_provisioning import create_and_activate_new_corpus_db, create_and_rebuild_new_corpus_db, resolve_existing_corpus_db_path
from .semantic_backfill import backfill_semantics
from .semantic_merge_ops import merge_corpus_databases, merge_preflight
from .semantic_release_ops import activation_preflight, apply_semantic_release, load_semantic_release
from .semantic_status import audit_semantics, read_active_semantic_release, semantic_status

__all__ = [
    "activation_preflight",
    "apply_semantic_release",
    "audit_semantics",
    "backfill_semantics",
    "create_and_activate_new_corpus_db",
    "create_and_rebuild_new_corpus_db",
    "load_semantic_release",
    "merge_corpus_databases",
    "merge_preflight",
    "read_active_semantic_release",
    "resolve_existing_corpus_db_path",
    "semantic_status",
]
