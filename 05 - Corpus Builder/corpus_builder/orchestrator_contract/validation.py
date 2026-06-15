"""Hard contract validation for the Corpus Builder subprocess surface."""
from __future__ import annotations

from .types import (
    ACTION_NAMES,
    ActionName,
)
from .validation_debug import (
    parse_activate_corpus_context_command,
    parse_activation_preflight_command,
    parse_activate_semantic_release_command,
    parse_create_and_activate_new_corpus_db_command,
    parse_create_empty_corpus_db_command,
    parse_debug_run_command,
    parse_generate_embeddings_command,
    parse_healthcheck_command,
    parse_load_document_command,
    parse_scan_debug_input_command,
)
from .validation_suite import (
    parse_backfill_stale_command,
    parse_backfill_sql_from_merge_artifacts_command,
    parse_basic_relation_mining_command,
    parse_cleanup_pipeline_batch_materialization_command,
    parse_create_and_rebuild_new_corpus_db_command,
    parse_extract_sample_files_for_reingest_command,
    parse_export_command,
    parse_inspect_latest_pipeline_batch_command,
    parse_load_semantic_release_command,
    parse_merge_corpus_databases_command,
    parse_merge_preflight_command,
    parse_multi_source_merge_databases_command,
    parse_multi_source_merge_preflight_command,
    parse_preview_rebuild_from_artifacts_command,
    parse_read_database_analysis_evidence_command,
    parse_read_active_semantic_release_command,
    parse_reingest_pipeline_batch_command,
    parse_rebuild_from_artifacts_command,
    parse_reset_active_corpus_db_command,
    parse_restore_pipeline_batch_originals_command,
    parse_search_command,
    parse_semantic_audit_command,
    parse_semantic_status_command,
    parse_stats_command,
    parse_validate_artifact_tree_command,
    parse_write_merge_reconciliation_manifest_command,
)


def require_action(payload: dict) -> ActionName:
    body = request_body(payload)
    action = str(body.get("action") or body.get("owner_action") or "").strip()
    if action in ACTION_NAMES:
        return action
    raise ValueError(f"Unbekannte Aktion: {action or '<leer>'}")


def request_body(payload: dict) -> dict:
    if payload.get("schema_version") == "adapter.call_request.v1":
        inner = payload.get("request_payload")
        if isinstance(inner, dict):
            return inner
    return payload


__all__ = [
    "parse_activation_preflight_command",
    "parse_activate_corpus_context_command",
    "parse_activate_semantic_release_command",
    "parse_create_and_activate_new_corpus_db_command",
    "parse_create_empty_corpus_db_command",
    "parse_backfill_stale_command",
    "parse_create_and_rebuild_new_corpus_db_command",
    "parse_validate_artifact_tree_command",
    "parse_read_database_analysis_evidence_command",
    "parse_inspect_latest_pipeline_batch_command",
    "parse_extract_sample_files_for_reingest_command",
    "parse_restore_pipeline_batch_originals_command",
    "parse_cleanup_pipeline_batch_materialization_command",
    "parse_reingest_pipeline_batch_command",
    "parse_multi_source_merge_preflight_command",
    "parse_multi_source_merge_databases_command",
    "parse_write_merge_reconciliation_manifest_command",
    "parse_backfill_sql_from_merge_artifacts_command",
    "parse_basic_relation_mining_command",
    "parse_debug_run_command",
    "parse_export_command",
    "parse_generate_embeddings_command",
    "parse_healthcheck_command",
    "parse_load_document_command",
    "parse_read_active_semantic_release_command",
    "parse_load_semantic_release_command",
    "parse_merge_corpus_databases_command",
    "parse_merge_preflight_command",
    "parse_preview_rebuild_from_artifacts_command",
    "parse_rebuild_from_artifacts_command",
    "parse_reset_active_corpus_db_command",
    "parse_scan_debug_input_command",
    "parse_search_command",
    "parse_semantic_audit_command",
    "parse_semantic_status_command",
    "parse_stats_command",
    "require_action",
    "request_body",
]
