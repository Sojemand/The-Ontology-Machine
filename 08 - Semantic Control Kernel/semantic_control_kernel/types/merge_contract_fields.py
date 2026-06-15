from __future__ import annotations


SOURCE_IDENTITY_ORIGINS: tuple[str, ...] = (
    "durable_owner_id",
    "kernel_import_local_id",
    "user_bound_artifact_root",
)

PROJECTION_MERGE_MODE_PRESERVE = "preserve_source_projections"
PROJECTION_MERGE_MODE_SINGLE = "merge_to_single_projection"
PROJECTION_MERGE_MODE_DEFAULT = PROJECTION_MERGE_MODE_PRESERVE
PROJECTION_MERGE_MODE_VALUES: tuple[str, ...] = (
    PROJECTION_MERGE_MODE_PRESERVE,
    PROJECTION_MERGE_MODE_SINGLE,
)

MERGE_SELECTION_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "merge_run_id", "created_at", "selected_by_interaction_id",
    "source_databases", "target_artifact_root", "target_database_path",
    "merge_route", "projection_merge_mode", "selection_fingerprint",
)

MERGE_SOURCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_database_id", "source_database_path", "source_artifact_root",
    "source_state", "source_semantic_release_id", "source_semantic_release_version",
    "source_release_fingerprint", "source_database_fingerprint",
    "source_artifact_tree_fingerprint", "source_identity_origin",
)

MERGE_COLLISION_REQUIRED_FIELDS: tuple[str, ...] = (
    "collision_id", "collision_class", "source_refs", "target_ref",
    "default_policy", "resolution_owner", "resolution_status",
    "selected_resolution", "requires_user_choice", "blocks_activation", "diagnostics",
)

MERGE_ID_MAP_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_database_id", "source_database_path", "source_record_id",
    "source_document_id", "source_original_file_name", "source_content_hash",
    "source_artifact_path", "source_pipeline_batch_id", "source_embedding_id",
    "target_record_id", "target_document_id", "target_artifact_path",
    "target_pipeline_batch_id", "target_embedding_id", "semantic_release_id",
    "semantic_release_version", "release_fingerprint", "taxonomy_fingerprint",
    "projection_id", "projection_fingerprint",
)
