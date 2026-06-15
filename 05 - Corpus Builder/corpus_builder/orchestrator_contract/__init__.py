"""Path-stable surface for the Corpus Builder subprocess contract."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..context import ModuleContext
from . import adapter, validation, workflow

CONTEXT = ModuleContext.from_package_root()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    CONTEXT.ensure_runtime_dirs()

    try:
        response = workflow.dispatch(
            adapter.load_request(Path(args.request)),
            context=CONTEXT,
            parse_debug_run_command_fn=validation.parse_debug_run_command,
            parse_scan_debug_input_command_fn=validation.parse_scan_debug_input_command,
            require_action_fn=validation.require_action,
            request_body_fn=validation.request_body,
            parse_activate_corpus_context_command_fn=validation.parse_activate_corpus_context_command,
            parse_activate_semantic_release_command_fn=validation.parse_activate_semantic_release_command,
            parse_create_empty_corpus_db_command_fn=validation.parse_create_empty_corpus_db_command,
            parse_reset_active_corpus_db_command_fn=validation.parse_reset_active_corpus_db_command,
            parse_create_and_activate_new_corpus_db_command_fn=validation.parse_create_and_activate_new_corpus_db_command,
            parse_activation_preflight_command_fn=validation.parse_activation_preflight_command,
            parse_generate_embeddings_command_fn=validation.parse_generate_embeddings_command,
            parse_healthcheck_command_fn=validation.parse_healthcheck_command,
            parse_load_document_command_fn=validation.parse_load_document_command,
            parse_semantic_status_command_fn=validation.parse_semantic_status_command,
            parse_read_active_semantic_release_command_fn=validation.parse_read_active_semantic_release_command,
            parse_load_semantic_release_command_fn=validation.parse_load_semantic_release_command,
            parse_semantic_audit_command_fn=validation.parse_semantic_audit_command,
            parse_backfill_stale_command_fn=validation.parse_backfill_stale_command,
            parse_merge_preflight_command_fn=validation.parse_merge_preflight_command,
            parse_merge_corpus_databases_command_fn=validation.parse_merge_corpus_databases_command,
            parse_validate_artifact_tree_command_fn=validation.parse_validate_artifact_tree_command,
            parse_read_database_analysis_evidence_command_fn=validation.parse_read_database_analysis_evidence_command,
            parse_inspect_latest_pipeline_batch_command_fn=validation.parse_inspect_latest_pipeline_batch_command,
            parse_extract_sample_files_for_reingest_command_fn=validation.parse_extract_sample_files_for_reingest_command,
            parse_restore_pipeline_batch_originals_command_fn=validation.parse_restore_pipeline_batch_originals_command,
            parse_cleanup_pipeline_batch_materialization_command_fn=validation.parse_cleanup_pipeline_batch_materialization_command,
            parse_reingest_pipeline_batch_command_fn=validation.parse_reingest_pipeline_batch_command,
            parse_multi_source_merge_preflight_command_fn=validation.parse_multi_source_merge_preflight_command,
            parse_multi_source_merge_databases_command_fn=validation.parse_multi_source_merge_databases_command,
            parse_write_merge_reconciliation_manifest_command_fn=validation.parse_write_merge_reconciliation_manifest_command,
            parse_backfill_sql_from_merge_artifacts_command_fn=validation.parse_backfill_sql_from_merge_artifacts_command,
            parse_basic_relation_mining_command_fn=validation.parse_basic_relation_mining_command,
            parse_search_command_fn=validation.parse_search_command,
            parse_stats_command_fn=validation.parse_stats_command,
            parse_export_command_fn=validation.parse_export_command,
            parse_preview_rebuild_from_artifacts_command_fn=validation.parse_preview_rebuild_from_artifacts_command,
            parse_rebuild_from_artifacts_command_fn=validation.parse_rebuild_from_artifacts_command,
            parse_create_and_rebuild_new_corpus_db_command_fn=validation.parse_create_and_rebuild_new_corpus_db_command,
        )
    except Exception as exc:  # pragma: no cover - defensive
        response = workflow.error_response(str(exc))
    adapter.write_response(Path(args.response), response)
    return 0


__all__ = ["adapter", "main", "validation", "workflow"]
