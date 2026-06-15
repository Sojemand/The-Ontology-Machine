from __future__ import annotations

from typing import Any

from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_DEFINITIONS
from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS
from semantic_control_kernel.types.agent_tools import empty_model_visible_schema


AGENT_EMPTY_OBJECT_SCHEMA: dict[str, Any] = empty_model_visible_schema()
EVENT_SCOPED_EMPTY_OBJECT_SCHEMA: dict[str, Any] = empty_model_visible_schema()
RESUME_CONTINUE_TOOL_NAME = "kernel_continue_resumable_workflow"
RESUME_CONTINUE_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "resume_option_ref": {
            "type": "string",
            "description": "Opaque Kernel resume option ref returned by kernel_resume_state.",
        },
    },
    "required": ["resume_option_ref"],
    "additionalProperties": False,
}

PERMANENT_AGENT_TOOL_NAMES: tuple[str, ...] = tuple(
    definition.tool_name for definition in PERMANENT_AGENT_TOOL_DEFINITIONS
)
PERMANENT_AGENT_TOOL_DESCRIPTION_MAP: dict[str, str] = {
    definition.tool_name: definition.description
    for definition in PERMANENT_AGENT_TOOL_DEFINITIONS
}
PERMANENT_AGENT_TOOL_SCHEMA_MAP: dict[str, dict[str, Any]] = {
    RESUME_CONTINUE_TOOL_NAME: RESUME_CONTINUE_TOOL_SCHEMA,
}

EVENT_SCOPED_RECOVERY_TOOL_NAMES: tuple[str, ...] = tuple(
    definition.tool_name for definition in EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS
)
EVENT_SCOPED_RECOVERY_TOOL_DESCRIPTION_MAP: dict[str, str] = {
    definition.tool_name: definition.description
    for definition in EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS
}

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
