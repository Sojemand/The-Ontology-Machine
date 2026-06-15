"""Path-stable operation handlers for the Corpus Builder contract."""

from __future__ import annotations

from ..services import (
    activate_corpus_context,
    activation_preflight,
    apply_semantic_release,
    audit_semantics,
    backfill_semantics,
    create_and_activate_new_corpus_db,
    create_and_rebuild_new_corpus_db,
    create_empty_corpus_db,
    export_corpus,
    get_stats,
    load_semantic_release,
    merge_corpus_databases,
    merge_preflight,
    read_active_semantic_release,
    reset_active_corpus_db,
    run_basic_relation_mining,
    search_corpus,
    semantic_status,
)
from ..standalone_artifacts import build_rebuild_bundles_from_artifacts, rebuild_corpus_from_artifacts
from . import workflow_suite_corpus as _corpus
from . import workflow_suite_ontology as _ontology
from . import workflow_suite_rebuild as _rebuild
from . import workflow_suite_semantic as _semantic


def handle_activate_corpus_context(command, *, context):
    return _corpus.handle_activate_corpus_context(command, context=context, activate_corpus_context_fn=activate_corpus_context)


def handle_create_empty_corpus_db(command, *, context):
    return _corpus.handle_create_empty_corpus_db(command, context=context, create_empty_corpus_db_fn=create_empty_corpus_db)


def handle_reset_active_corpus_db(command, *, context):
    return _corpus.handle_reset_active_corpus_db(command, context=context, reset_active_corpus_db_fn=reset_active_corpus_db)


def handle_create_and_activate_new_corpus_db(command, *, context):
    return _corpus.handle_create_and_activate_new_corpus_db(
        command,
        context=context,
        create_and_activate_new_corpus_db_fn=create_and_activate_new_corpus_db,
        apply_semantic_release_fn=apply_semantic_release,
    )


def handle_search(command, *, context):
    return _corpus.handle_search(command, context=context, search_corpus_fn=search_corpus)


def handle_stats(command, *, context):
    return _corpus.handle_stats(command, context=context, get_stats_fn=get_stats)


def handle_basic_relation_mining(command, *, context):
    return _ontology.handle_basic_relation_mining(command, context=context, run_basic_relation_mining_fn=run_basic_relation_mining)


def handle_export(command, *, context):
    return _corpus.handle_export(command, context=context, export_corpus_fn=export_corpus)


def handle_semantic_status(command, *, context):
    return _semantic.handle_semantic_status(command, context=context, semantic_status_fn=semantic_status)


def handle_read_active_semantic_release(command, *, context):
    return _semantic.handle_read_active_semantic_release(
        command,
        context=context,
        read_active_semantic_release_fn=read_active_semantic_release,
    )


def handle_load_semantic_release(command, *, context):
    return _semantic.handle_load_semantic_release(command, context=context, load_semantic_release_fn=load_semantic_release)


def handle_activation_preflight(command, *, context):
    return _semantic.handle_activation_preflight(command, context=context, activation_preflight_fn=activation_preflight)


def handle_semantic_audit(command, *, context):
    return _semantic.handle_semantic_audit(command, context=context, audit_semantics_fn=audit_semantics)


def handle_backfill_stale(command, *, context):
    return _semantic.handle_backfill_stale(command, context=context, backfill_semantics_fn=backfill_semantics)


def handle_merge_preflight(command, *, context):
    return _semantic.handle_merge_preflight(command, context=context, merge_preflight_fn=merge_preflight)


def handle_merge_corpus_databases(command, *, context):
    return _semantic.handle_merge_corpus_databases(command, context=context, merge_corpus_databases_fn=merge_corpus_databases)


def handle_preview_rebuild(command, *, context):
    return _rebuild.handle_preview_rebuild(
        command,
        context=context,
        build_rebuild_bundles_from_artifacts_fn=build_rebuild_bundles_from_artifacts,
    )


def handle_rebuild(command, *, context):
    return _rebuild.handle_rebuild(command, context=context, rebuild_corpus_from_artifacts_fn=rebuild_corpus_from_artifacts)


def handle_create_and_rebuild_new_corpus_db(command, *, context):
    return _rebuild.handle_create_and_rebuild_new_corpus_db(
        command,
        context=context,
        create_and_rebuild_new_corpus_db_fn=create_and_rebuild_new_corpus_db,
        rebuild_corpus_from_artifacts_fn=rebuild_corpus_from_artifacts,
    )


__all__ = [
    "activate_corpus_context",
    "activation_preflight",
    "apply_semantic_release",
    "audit_semantics",
    "backfill_semantics",
    "build_rebuild_bundles_from_artifacts",
    "create_and_activate_new_corpus_db",
    "create_and_rebuild_new_corpus_db",
    "create_empty_corpus_db",
    "export_corpus",
    "get_stats",
    "handle_activate_corpus_context",
    "handle_activation_preflight",
    "handle_backfill_stale",
    "handle_basic_relation_mining",
    "handle_create_and_activate_new_corpus_db",
    "handle_create_and_rebuild_new_corpus_db",
    "handle_create_empty_corpus_db",
    "handle_export",
    "handle_load_semantic_release",
    "handle_merge_corpus_databases",
    "handle_merge_preflight",
    "handle_preview_rebuild",
    "handle_read_active_semantic_release",
    "handle_rebuild",
    "handle_reset_active_corpus_db",
    "handle_search",
    "handle_semantic_audit",
    "handle_semantic_status",
    "handle_stats",
    "load_semantic_release",
    "merge_corpus_databases",
    "merge_preflight",
    "read_active_semantic_release",
    "rebuild_corpus_from_artifacts",
    "reset_active_corpus_db",
    "run_basic_relation_mining",
    "search_corpus",
    "semantic_status",
]
