"""Dispatch table for the Corpus Builder subprocess contract."""

from __future__ import annotations

from ..context import ModuleContext
from . import debug_workflow
from .types import (
    ACTIVATE_CORPUS_CONTEXT_ACTION,
    ACTIVATE_SEMANTIC_RELEASE_ACTION,
    ACTIVATION_PREFLIGHT_ACTION,
    BACKFILL_SQL_FROM_MERGE_ARTIFACTS_ACTION,
    BACKFILL_STALE_ACTION,
    BASIC_RELATION_MINING_ACTION,
    CLEANUP_PIPELINE_BATCH_MATERIALIZATION_ACTION,
    CREATE_AND_ACTIVATE_NEW_CORPUS_DB_ACTION,
    CREATE_AND_REBUILD_NEW_CORPUS_DB_ACTION,
    CREATE_EMPTY_CORPUS_DB_ACTION,
    DEBUG_RUN_ACTION,
    EXTRACT_SAMPLE_FILES_FOR_REINGEST_ACTION,
    EXPORT_ACTION,
    GENERATE_EMBEDDINGS_ACTION,
    HEALTHCHECK_ACTION,
    INSPECT_LATEST_PIPELINE_BATCH_ACTION,
    LOAD_DOCUMENT_ACTION,
    LOAD_SEMANTIC_RELEASE_ACTION,
    MERGE_CORPUS_DATABASES_ACTION,
    MERGE_PREFLIGHT_ACTION,
    MULTI_SOURCE_MERGE_DATABASES_ACTION,
    MULTI_SOURCE_MERGE_PREFLIGHT_ACTION,
    PREVIEW_REBUILD_FROM_ARTIFACTS_ACTION,
    READ_DATABASE_ANALYSIS_EVIDENCE_ACTION,
    READ_ACTIVE_SEMANTIC_RELEASE_ACTION,
    REINGEST_PIPELINE_BATCH_ACTION,
    REBUILD_FROM_ARTIFACTS_ACTION,
    RESET_ACTIVE_CORPUS_DB_ACTION,
    RESTORE_PIPELINE_BATCH_ORIGINALS_ACTION,
    SCAN_DEBUG_INPUT_ACTION,
    SEARCH_ACTION,
    SEMANTIC_AUDIT_ACTION,
    SEMANTIC_STATUS_ACTION,
    STATS_ACTION,
    VALIDATE_ARTIFACT_TREE_ACTION,
    WRITE_MERGE_RECONCILIATION_MANIFEST_ACTION,
)
from .workflow_core import activate_semantic_release, error_response, generate_embeddings, load_document
from .workflow_healthcheck import healthcheck
from .workflow_suite import (
    handle_activate_corpus_context,
    handle_activation_preflight,
    handle_backfill_stale,
    handle_basic_relation_mining,
    handle_create_and_activate_new_corpus_db,
    handle_create_and_rebuild_new_corpus_db,
    handle_create_empty_corpus_db,
    handle_export,
    handle_load_semantic_release,
    handle_merge_corpus_databases,
    handle_merge_preflight,
    handle_preview_rebuild,
    handle_read_active_semantic_release,
    handle_rebuild,
    handle_reset_active_corpus_db,
    handle_search,
    handle_semantic_audit,
    handle_semantic_status,
    handle_stats,
)
from .workflow_suite_phase19 import (
    handle_backfill_sql_from_merge_artifacts,
    handle_cleanup_pipeline_batch_materialization,
    handle_extract_sample_files_for_reingest,
    handle_inspect_latest_pipeline_batch,
    handle_multi_source_merge_databases,
    handle_multi_source_merge_preflight,
    handle_read_database_analysis_evidence,
    handle_reingest_pipeline_batch,
    handle_restore_pipeline_batch_originals,
    handle_validate_artifact_tree,
    handle_write_merge_reconciliation_manifest,
)


def dispatch(payload: dict, *, context: ModuleContext, **parsers) -> dict:
    body = parsers["request_body_fn"](payload) if "request_body_fn" in parsers else payload
    action = parsers["require_action_fn"](payload)
    if action == LOAD_DOCUMENT_ACTION:
        return load_document(parsers["parse_load_document_command_fn"](body), context=context)
    if action == ACTIVATE_SEMANTIC_RELEASE_ACTION:
        return activate_semantic_release(parsers["parse_activate_semantic_release_command_fn"](body), context=context)
    if action == GENERATE_EMBEDDINGS_ACTION:
        return generate_embeddings(parsers["parse_generate_embeddings_command_fn"](body), context=context)
    if action == HEALTHCHECK_ACTION:
        return healthcheck(parsers["parse_healthcheck_command_fn"](body), context=context)
    if action in _SUITE_HANDLERS:
        return _dispatch_suite(action, body, context=context, parsers=parsers)
    if action == SCAN_DEBUG_INPUT_ACTION:
        return debug_workflow.run_scan(body, context=context, parse_scan_debug_input_command_fn=parsers["parse_scan_debug_input_command_fn"])
    if action == DEBUG_RUN_ACTION:
        return debug_workflow.run_debug(body, context=context, parse_debug_run_command_fn=parsers["parse_debug_run_command_fn"])
    return error_response(f"Unbekannte Aktion: {action}")


def _dispatch_suite(action: str, payload: dict, *, context: ModuleContext, parsers: dict) -> dict:
    parser_name, handler = _SUITE_HANDLERS[action]
    parser = parsers.get(parser_name)
    if parser is None:
        raise ValueError(f"Parser fuer {action} fehlt.")
    return handler(parser(payload), context=context)


_SUITE_HANDLERS = {
    ACTIVATE_CORPUS_CONTEXT_ACTION: ("parse_activate_corpus_context_command_fn", handle_activate_corpus_context),
    CREATE_EMPTY_CORPUS_DB_ACTION: ("parse_create_empty_corpus_db_command_fn", handle_create_empty_corpus_db),
    RESET_ACTIVE_CORPUS_DB_ACTION: ("parse_reset_active_corpus_db_command_fn", handle_reset_active_corpus_db),
    CREATE_AND_ACTIVATE_NEW_CORPUS_DB_ACTION: ("parse_create_and_activate_new_corpus_db_command_fn", handle_create_and_activate_new_corpus_db),
    ACTIVATION_PREFLIGHT_ACTION: ("parse_activation_preflight_command_fn", handle_activation_preflight),
    SEMANTIC_STATUS_ACTION: ("parse_semantic_status_command_fn", handle_semantic_status),
    READ_ACTIVE_SEMANTIC_RELEASE_ACTION: ("parse_read_active_semantic_release_command_fn", handle_read_active_semantic_release),
    LOAD_SEMANTIC_RELEASE_ACTION: ("parse_load_semantic_release_command_fn", handle_load_semantic_release),
    SEMANTIC_AUDIT_ACTION: ("parse_semantic_audit_command_fn", handle_semantic_audit),
    BACKFILL_STALE_ACTION: ("parse_backfill_stale_command_fn", handle_backfill_stale),
    MERGE_PREFLIGHT_ACTION: ("parse_merge_preflight_command_fn", handle_merge_preflight),
    MERGE_CORPUS_DATABASES_ACTION: ("parse_merge_corpus_databases_command_fn", handle_merge_corpus_databases),
    VALIDATE_ARTIFACT_TREE_ACTION: ("parse_validate_artifact_tree_command_fn", handle_validate_artifact_tree),
    READ_DATABASE_ANALYSIS_EVIDENCE_ACTION: ("parse_read_database_analysis_evidence_command_fn", handle_read_database_analysis_evidence),
    INSPECT_LATEST_PIPELINE_BATCH_ACTION: ("parse_inspect_latest_pipeline_batch_command_fn", handle_inspect_latest_pipeline_batch),
    EXTRACT_SAMPLE_FILES_FOR_REINGEST_ACTION: ("parse_extract_sample_files_for_reingest_command_fn", handle_extract_sample_files_for_reingest),
    RESTORE_PIPELINE_BATCH_ORIGINALS_ACTION: ("parse_restore_pipeline_batch_originals_command_fn", handle_restore_pipeline_batch_originals),
    CLEANUP_PIPELINE_BATCH_MATERIALIZATION_ACTION: ("parse_cleanup_pipeline_batch_materialization_command_fn", handle_cleanup_pipeline_batch_materialization),
    REINGEST_PIPELINE_BATCH_ACTION: ("parse_reingest_pipeline_batch_command_fn", handle_reingest_pipeline_batch),
    MULTI_SOURCE_MERGE_PREFLIGHT_ACTION: ("parse_multi_source_merge_preflight_command_fn", handle_multi_source_merge_preflight),
    MULTI_SOURCE_MERGE_DATABASES_ACTION: ("parse_multi_source_merge_databases_command_fn", handle_multi_source_merge_databases),
    WRITE_MERGE_RECONCILIATION_MANIFEST_ACTION: ("parse_write_merge_reconciliation_manifest_command_fn", handle_write_merge_reconciliation_manifest),
    BACKFILL_SQL_FROM_MERGE_ARTIFACTS_ACTION: ("parse_backfill_sql_from_merge_artifacts_command_fn", handle_backfill_sql_from_merge_artifacts),
    SEARCH_ACTION: ("parse_search_command_fn", handle_search),
    STATS_ACTION: ("parse_stats_command_fn", handle_stats),
    EXPORT_ACTION: ("parse_export_command_fn", handle_export),
    PREVIEW_REBUILD_FROM_ARTIFACTS_ACTION: ("parse_preview_rebuild_from_artifacts_command_fn", handle_preview_rebuild),
    CREATE_AND_REBUILD_NEW_CORPUS_DB_ACTION: ("parse_create_and_rebuild_new_corpus_db_command_fn", handle_create_and_rebuild_new_corpus_db),
    REBUILD_FROM_ARTIFACTS_ACTION: ("parse_rebuild_from_artifacts_command_fn", handle_rebuild),
    BASIC_RELATION_MINING_ACTION: ("parse_basic_relation_mining_command_fn", handle_basic_relation_mining),
}
