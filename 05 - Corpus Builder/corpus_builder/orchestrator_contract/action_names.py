"""Action-name constants for the Corpus Builder subprocess contract."""

from __future__ import annotations

from typing import Literal

DEBUG_RUN_ACTION = "debug_run"
SCAN_DEBUG_INPUT_ACTION = "scan_debug_input"
LOAD_DOCUMENT_ACTION = "load_document"
ACTIVATE_SEMANTIC_RELEASE_ACTION = "activate_semantic_release"
ACTIVATE_CORPUS_CONTEXT_ACTION = "activate_corpus_context"
CREATE_EMPTY_CORPUS_DB_ACTION = "create_empty_corpus_db"
RESET_ACTIVE_CORPUS_DB_ACTION = "reset_active_corpus_db"
CREATE_AND_ACTIVATE_NEW_CORPUS_DB_ACTION = "create_and_activate_new_corpus_db"
ACTIVATION_PREFLIGHT_ACTION = "activation_preflight"
GENERATE_EMBEDDINGS_ACTION = "generate_embeddings"
HEALTHCHECK_ACTION = "healthcheck"
SEMANTIC_STATUS_ACTION = "semantic_status"
READ_ACTIVE_SEMANTIC_RELEASE_ACTION = "read_active_semantic_release"
LOAD_SEMANTIC_RELEASE_ACTION = "load_semantic_release"
SEMANTIC_AUDIT_ACTION = "semantic_audit"
BACKFILL_STALE_ACTION = "backfill_stale"
MERGE_PREFLIGHT_ACTION = "merge_preflight"
MERGE_CORPUS_DATABASES_ACTION = "merge_corpus_databases"
VALIDATE_ARTIFACT_TREE_ACTION = "validate_artifact_tree"
READ_DATABASE_ANALYSIS_EVIDENCE_ACTION = "read_database_analysis_evidence"
INSPECT_LATEST_PIPELINE_BATCH_ACTION = "inspect_latest_pipeline_batch"
EXTRACT_SAMPLE_FILES_FOR_REINGEST_ACTION = "extract_sample_files_for_reingest"
RESTORE_PIPELINE_BATCH_ORIGINALS_ACTION = "restore_pipeline_batch_originals"
CLEANUP_PIPELINE_BATCH_MATERIALIZATION_ACTION = "cleanup_pipeline_batch_materialization"
REINGEST_PIPELINE_BATCH_ACTION = "reingest_pipeline_batch"
MULTI_SOURCE_MERGE_PREFLIGHT_ACTION = "multi_source_merge_preflight"
MULTI_SOURCE_MERGE_DATABASES_ACTION = "multi_source_merge_databases"
WRITE_MERGE_RECONCILIATION_MANIFEST_ACTION = "write_merge_reconciliation_manifest"
BACKFILL_SQL_FROM_MERGE_ARTIFACTS_ACTION = "backfill_sql_from_merge_artifacts"
SEARCH_ACTION = "search"
STATS_ACTION = "stats"
EXPORT_ACTION = "export"
PREVIEW_REBUILD_FROM_ARTIFACTS_ACTION = "preview_rebuild_from_artifacts"
REBUILD_FROM_ARTIFACTS_ACTION = "rebuild_from_artifacts"
CREATE_AND_REBUILD_NEW_CORPUS_DB_ACTION = "create_and_rebuild_new_corpus_db"
BASIC_RELATION_MINING_ACTION = "basic_relation_mining"

ACTION_NAMES = (
    LOAD_DOCUMENT_ACTION,
    ACTIVATE_SEMANTIC_RELEASE_ACTION,
    ACTIVATE_CORPUS_CONTEXT_ACTION,
    CREATE_EMPTY_CORPUS_DB_ACTION,
    RESET_ACTIVE_CORPUS_DB_ACTION,
    CREATE_AND_ACTIVATE_NEW_CORPUS_DB_ACTION,
    ACTIVATION_PREFLIGHT_ACTION,
    GENERATE_EMBEDDINGS_ACTION,
    HEALTHCHECK_ACTION,
    SCAN_DEBUG_INPUT_ACTION,
    DEBUG_RUN_ACTION,
    SEMANTIC_STATUS_ACTION,
    READ_ACTIVE_SEMANTIC_RELEASE_ACTION,
    LOAD_SEMANTIC_RELEASE_ACTION,
    SEMANTIC_AUDIT_ACTION,
    BACKFILL_STALE_ACTION,
    MERGE_PREFLIGHT_ACTION,
    MERGE_CORPUS_DATABASES_ACTION,
    VALIDATE_ARTIFACT_TREE_ACTION,
    READ_DATABASE_ANALYSIS_EVIDENCE_ACTION,
    INSPECT_LATEST_PIPELINE_BATCH_ACTION,
    EXTRACT_SAMPLE_FILES_FOR_REINGEST_ACTION,
    RESTORE_PIPELINE_BATCH_ORIGINALS_ACTION,
    CLEANUP_PIPELINE_BATCH_MATERIALIZATION_ACTION,
    REINGEST_PIPELINE_BATCH_ACTION,
    MULTI_SOURCE_MERGE_PREFLIGHT_ACTION,
    MULTI_SOURCE_MERGE_DATABASES_ACTION,
    WRITE_MERGE_RECONCILIATION_MANIFEST_ACTION,
    BACKFILL_SQL_FROM_MERGE_ARTIFACTS_ACTION,
    SEARCH_ACTION,
    STATS_ACTION,
    EXPORT_ACTION,
    PREVIEW_REBUILD_FROM_ARTIFACTS_ACTION,
    REBUILD_FROM_ARTIFACTS_ACTION,
    CREATE_AND_REBUILD_NEW_CORPUS_DB_ACTION,
    BASIC_RELATION_MINING_ACTION,
)

ActionName = Literal[
    "debug_run",
    "scan_debug_input",
    "load_document",
    "activate_semantic_release",
    "activate_corpus_context",
    "create_empty_corpus_db",
    "reset_active_corpus_db",
    "create_and_activate_new_corpus_db",
    "activation_preflight",
    "generate_embeddings",
    "healthcheck",
    "semantic_status",
    "read_active_semantic_release",
    "load_semantic_release",
    "semantic_audit",
    "backfill_stale",
    "merge_preflight",
    "merge_corpus_databases",
    "validate_artifact_tree",
    "read_database_analysis_evidence",
    "inspect_latest_pipeline_batch",
    "extract_sample_files_for_reingest",
    "restore_pipeline_batch_originals",
    "cleanup_pipeline_batch_materialization",
    "reingest_pipeline_batch",
    "multi_source_merge_preflight",
    "multi_source_merge_databases",
    "write_merge_reconciliation_manifest",
    "backfill_sql_from_merge_artifacts",
    "search",
    "stats",
    "export",
    "preview_rebuild_from_artifacts",
    "rebuild_from_artifacts",
    "create_and_rebuild_new_corpus_db",
    "basic_relation_mining",
]
