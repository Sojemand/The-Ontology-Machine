from __future__ import annotations


_SEMANTIC_STATUS_KEYS = frozenset({"action", "corpus_db_path"})
_READ_ACTIVE_SEMANTIC_RELEASE_KEYS = frozenset({"action", "corpus_db_path"})
_LOAD_SEMANTIC_RELEASE_KEYS = frozenset({"action", "corpus_db_path", "release_path", "write_global_mirrors"})
_RESET_ACTIVE_CORPUS_DB_KEYS = frozenset({"action", "confirmation_artifact_path", "corpus_db_path"})
_SEMANTIC_AUDIT_KEYS = frozenset({"action", "corpus_db_path"})
_BACKFILL_STALE_KEYS = frozenset({"action", "corpus_db_path", "document_ids", "stale_only", "limit"})
_MERGE_PREFLIGHT_KEYS = frozenset({"action", "source_db_path", "target_db_path"})
_MERGE_CORPUS_DATABASES_KEYS = frozenset(
    {
        "action",
        "source_db_path",
        "target_db_path",
        "snapshot_risk_confirmation_artifact_path",
        "collision_resolution_artifact_path",
    }
)
_SEARCH_KEYS = frozenset({"action", "corpus_db_path", "limit", "mode", "query", "runtime_model"})
_STATS_KEYS = frozenset({"action", "corpus_db_path"})
_EXPORT_KEYS = frozenset({"action", "corpus_db_path", "fmt", "include_archived", "output_path"})
_PREVIEW_REBUILD_KEYS = frozenset(
    {"action", "corpus_db_path", "normalized_dir", "pipeline_root", "structured_dir", "validation_dir", "raw_dir", "release_path"}
)
_REBUILD_KEYS = frozenset(
    {
        "action",
        "corpus_db_path",
        "normalized_dir",
        "pipeline_root",
        "replace_existing",
        "structured_dir",
        "validation_dir",
        "raw_dir",
        "release_path",
    }
)
_CREATE_AND_REBUILD_NEW_CORPUS_DB_KEYS = frozenset(
    {"action", "confirmation_artifact_path", "normalized_dir", "pipeline_root", "structured_dir", "validation_dir", "raw_dir", "release_path"}
)
_BASIC_RELATION_MINING_KEYS = frozenset({"action", "corpus_db_path", "dry_run"})
_VALIDATE_ARTIFACT_TREE_KEYS = frozenset(
    {
        "owner_action",
        "schema_version",
        "workflow_run_id",
        "adapter_call_id",
        "requested_at",
        "artifact_root_path",
        "folder_contract_version",
        "target_identity",
        "require_empty_input",
        "require_semantic_release_folder",
        "require_corpus_folder",
        "return_unexpected_paths",
        "request_fingerprint",
    }
)
_DATABASE_ANALYSIS_KEYS = frozenset(
    {
        "owner_action",
        "schema_version",
        "workflow_run_id",
        "adapter_call_id",
        "requested_at",
        "database_path",
        "database_path_hash",
        "database_ref",
        "artifact_root",
        "semantic_release_ref",
        "active_release_ref",
        "release_materialization_refs",
        "analysis_scope",
        "target_identity",
        "query_manifest",
        "request_fingerprint",
    }
)
_PIPELINE_BATCH_KEYS = frozenset(
    {
        "owner_action",
        "schema_version",
        "workflow_run_id",
        "adapter_call_id",
        "requested_at",
        "database_ref",
        "artifact_root",
        "batch_kind_filter",
        "require_cleanup_targetable",
        "target_identity",
        "sample_count",
        "selection_policy",
        "semantic_release_ref",
        "target_input_path",
        "pipeline_batch_id",
        "all_originals_scope",
        "input_collision_policy",
        "cleanup_scope",
        "confirmation_receipt_ref",
        "destructive_plan_ref",
        "sample_selection_manifest_ref",
        "source_manifest_ref",
        "source_pipeline_batch_id",
        "input_refs",
        "new_pipeline_batch_id",
        "kernel_continuation_proof",
        "request_fingerprint",
    }
)
_MERGE_PHASE19_KEYS = frozenset(
    {
        "owner_action",
        "schema_version",
        "workflow_run_id",
        "adapter_call_id",
        "requested_at",
        "merge_run_id",
        "selection",
        "source_databases",
        "target_artifact_root",
        "target_database_path",
        "merge_route",
        "collision_policy_version",
        "target_identity",
        "collision_manifest_ref",
        "collision_manifest",
        "selected_resolutions",
        "confirmation_receipt_ref",
        "merge_mode",
        "mode",
        "id_map",
        "artifact_root",
        "backfill_scope",
        "request_fingerprint",
    }
)
