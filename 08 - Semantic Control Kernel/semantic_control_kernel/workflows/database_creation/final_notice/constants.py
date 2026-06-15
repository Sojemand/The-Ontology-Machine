from __future__ import annotations

from typing import Any

_DATABASE_CREATION_STEP_FACTS: dict[str, dict[str, Any]] = {
    "dc_create_artifact_tree": {"fact_id": "artifact_tree_created", "label": "Artifact Tree", "artifact_keys": ["artifact_root_path"]},
    "dc_create_empty_database": {"fact_id": "empty_database_created", "label": "empty Corpus DB", "artifact_keys": ["database_path"]},
    "dc_export_default_release": {"fact_id": "default_semantic_release_exported", "label": "Default Semantic Release export", "artifact_keys": ["default_release_export_path"]},
    "dc_write_default_release": {"fact_id": "default_semantic_release_written", "label": "Default Semantic Release file", "artifact_keys": ["default_release_path"]},
    "dc_attach_default_release": {"fact_id": "default_semantic_release_attached", "label": "Default Semantic Release attachment", "artifact_keys": ["default_release_path", "database_path"]},
    "dc_remove_default_projections": {"fact_id": "default_projections_removed", "label": "default projection removal", "artifact_keys": ["projectionless_release_state_path"]},
    "dc_activate_default_release": {"fact_id": "default_semantic_release_activated", "label": "Default Semantic Release activation", "artifact_keys": ["default_release_path", "database_path"]},
    "tax_stage_custom_taxonomy": {"fact_id": "custom_taxonomy_staged", "label": "custom taxonomy stage", "artifact_keys": ["custom_taxonomy_stage_path"]},
    "proj_stage_custom_projection": {"fact_id": "custom_projections_staged", "label": "custom projections stage"},
    "rel_write_custom_release": {"fact_id": "custom_semantic_release_written", "label": "custom Semantic Release file"},
    "rel_attach_custom_release": {"fact_id": "custom_semantic_release_attached", "label": "custom Semantic Release attachment"},
    "rel_activate_custom_release": {"fact_id": "custom_semantic_release_activated", "label": "custom Semantic Release activation"},
}

_DEFAULT_COMPLETION_STRUCTURE = ["what_was_created", "what_the_current_state_means", "next_step_options"]
_RESUMED_COMPLETION_STRUCTURE = ["already_available", "performed_this_run", "what_the_current_state_means", "next_step_options"]
_DEFAULT_BLOCKED_STRUCTURE = ["what_was_created", "why_the_workflow_stopped", "next_step_options"]
_RESUMED_BLOCKED_STRUCTURE = ["already_available", "performed_this_run", "why_the_workflow_stopped", "next_step_options"]
