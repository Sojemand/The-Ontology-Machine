from __future__ import annotations

from .semantic_control_kernel_tool_scopes import (
    EVENT_SCOPED_TOOL_SCOPE_FIELDS,
    FORWARDABLE_CLIENT_CONTEXT_FIELDS,
    HOST_ONLY_CLIENT_BRIDGE_REQUIRED_FIELDS,
    KERNEL_CONTINUATION_SCOPE_FIELDS,
    KERNEL_INTERNAL_SCOPE_FIELDS,
)

PERMANENT_AGENT_TOOL_NAMES: tuple[str, ...] = (
    "empty_database_no_semantic_release",
    "empty_database_default_taxonomy_no_projections",
    "empty_database_default_taxonomy_default_projections",
    "empty_database_default_taxonomy_custom_projections",
    "empty_database_custom_taxonomy_no_projections",
    "empty_database_custom_taxonomy_custom_projections",
    "manual_pipeline_run",
    "database_merge_additive_only",
    "database_rebuild_from_artifacts",
    "create_custom_taxonomy_path",
    "create_custom_projection_path",
    "reset_database",
    "kernel_status",
    "kernel_resume_state",
    "kernel_continue_resumable_workflow",
    "kernel_cancel_active_run",
)

EVENT_SCOPED_RECOVERY_TOOL_NAMES: tuple[str, ...] = (
    "kernel_apply_recovery_option",
    "kernel_open_recovery_dialog",
    "kernel_retry_recoverable_workflow",
    "kernel_resolve_stale_lock",
    "kernel_rebind_database_artifact_tree",
    "kernel_discard_or_archive_staged_work",
    "kernel_reconcile_partial_pipeline_run",
    "kernel_open_support_bundle",
)

KERNEL_INTERNAL_TOOL_NAMES: tuple[str, ...] = (
    "create_standard_artifact_folder_tree",
    "create_empty_database",
    "store_active_artifact_folder_tree",
    "write_semantic_release",
    "attach_semantic_release_to_database",
    "attach_default_semantic_release_to_database",
    "attach_custom_semantic_release_to_database",
    "activate_semantic_release",
    "stage_custom_taxonomy_for_semantic_release",
    "stage_custom_projections_for_semantic_release",
    "create_custom_semantic_release",
    "create_custom_taxonomy",
    "create_custom_projection",
    "validate_projections_against_taxonomy",
    "merge_database_empty",
    "merge_database_filled_additive",
    "merge_taxonomy_and_projections_additive",
    "reconcile_merged_semantic_release",
    "reconcile_merged_database",
    "write_combined_database",
    "fill_artifact_folder_tree",
    "backfill_sql",
    "corpus_builder_load_semantic_release",
    "run_corpus_builder",
    "create_embeddings",
    "basic_relation_mining",
    "ontology_patch_validation",
)

KERNEL_CONTINUATION_TOOL_NAMES: tuple[str, ...] = ()

HOST_ONLY_CLIENT_BRIDGE_NAMES: tuple[str, ...] = (
    "kernel_list_client_frontend_events",
    "kernel_submit_user_interaction_response",
    "kernel_cancel_user_interaction",
    "kernel_list_event_scoped_tool_definitions",
)


def _legacy_name(*parts: str) -> str:
    return "_".join(parts)


LEGACY_RETIRED_TOOL_NAMES: tuple[str, ...] = (
    _legacy_name("llm", "action", "catalog"),
    _legacy_name("open", "workflow"),
    _legacy_name("inspect", "workflow"),
    _legacy_name("execute", "readonly", "workflow", "action"),
    _legacy_name("execute", "author", "workflow", "action"),
    _legacy_name("execute", "operator", "workflow", "action"),
    _legacy_name("execute", "admin", "workflow", "action"),
    _legacy_name("interrupt", "workflow"),
    _legacy_name("close", "workflow"),
)

NON_AGENT_INTERNAL_ALLOWLIST: frozenset[str] = frozenset(
    EVENT_SCOPED_RECOVERY_TOOL_NAMES
    + KERNEL_INTERNAL_TOOL_NAMES
    + KERNEL_CONTINUATION_TOOL_NAMES
    + HOST_ONLY_CLIENT_BRIDGE_NAMES
)
