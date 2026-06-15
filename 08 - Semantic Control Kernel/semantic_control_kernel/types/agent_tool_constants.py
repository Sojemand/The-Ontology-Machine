from __future__ import annotations

AGENT_TOOL_DEFINITION_SCHEMA_VERSION = "agent_tool_definition.v1"
AGENT_TOOL_SURFACE_INVENTORY_SCHEMA_VERSION = "agent_tool_surface_inventory.v1"
AGENT_TOOL_INVOCATION_SCHEMA_VERSION = "agent_tool_invocation.v1"
AGENT_TOOL_RESULT_SCHEMA_VERSION = "agent_tool_result.v1"
AGENT_TOOL_SURFACE_VERSION = "phase7.agent_surface.v1"

AGENT_TOOL_VISIBILITIES = ("permanent", "event_scoped")
AGENT_TOOL_LAYERS = (
    "primary_workflow",
    "continuation_loop",
    "support_control",
    "recovery_control",
)
AGENT_TOOL_HANDLER_STATUSES = (
    "surface_only_until_phase_9",
    "surface_only_until_phase_10",
    "surface_only_until_phase_11",
    "surface_only_until_phase_12",
    "implemented_phase_7",
    "event_scoped_until_phase_13",
)
ALLOWED_INVOCATION_CONTEXT_FIELDS = frozenset(
    {
        "host_surface_identity",
        "conversation_ref",
        "turn_ref",
        "visible_context_ref",
        "client_request_id",
        "client_injected",
        "user_request_ref",
    }
)


def _legacy_name(*parts: str) -> str:
    return "_".join(parts)


FORBIDDEN_MODEL_AUTHORED_FIELDS = frozenset(
    {
        "artifact_root_path",
        "target_database_path",
        "database_name",
        "input_folder_path",
        "selected_resume_id",
        "pending_interaction_id",
        "confirmation_id",
        "recovery_id",
        _legacy_name("workflow", "family", "id"),
        _legacy_name("action", "token"),
        _legacy_name("target", "action", "id"),
        "permission_level",
        "pipeline_action",
    }
)
REJECTED_LEGACY_AGENT_SURFACE_NAMES = (
    _legacy_name("llm", "action", "catalog"),
    _legacy_name("open", "workflow"),
    _legacy_name("inspect", "workflow"),
    _legacy_name("execute", "readonly", "workflow", "action"),
    _legacy_name("execute", "author", "workflow", "action"),
    _legacy_name("execute", "operator", "workflow", "action"),
    _legacy_name("execute", "admin", "workflow", "action"),
    _legacy_name("execute", "workflow", "action"),
    _legacy_name("workflow", "family", "id"),
    _legacy_name("workflow", "revision"),
    _legacy_name("action", "token"),
    "pipeline_action",
    "pipeline_continue",
    _legacy_name("target", "action", "id"),
    "permission_level",
    "kernel_create_database",
    "kernel_modify_rules",
    "kernel_run_pipeline",
    "kernel_merge_databases",
    "kernel_rebuild_database",
)
