from __future__ import annotations

from semantic_control_kernel.types.agent_tools import AgentToolDefinition, empty_model_visible_schema


AGENT_SURFACE_CONTEXT_PREAMBLE = (
    "The Vision Pipeline turns source documents into a semantic Corpus database "
    "and Artifact Tree. A Semantic Release contains taxonomy and projections. "
    "Empty and filled databases use different workflow safety policy. Batch "
    "manifests make manual ingestion auditable. The Kernel owns "
    "workflow execution, state validation, dialogs, blockers, confirmations, "
    "resume state and adapter calls. The Agent chooses only the workflow tool "
    "from user intent and may explain mirrored Kernel state, but it does not "
    "collect Kernel-required values. A new primary workflow request starts new "
    "work; resume requires explicit Kernel resume options and the generic "
    "resume-continue tool."
)

GENERATED_FROM_SPEC_REFS = (
    "Semantic Kernel SPEC/05_database_creation_workflows.md",
    "Semantic Kernel SPEC/07_pipeline_merge_rebuild_workflows.md",
    "Semantic Kernel SPEC/10_kernel_only_functions.md",
    "Semantic Kernel SPEC/11_kernel_internal_data_contracts.md",
    "Semantic Kernel SPEC/23_agent_facing_pipeline_manager_tools.md",
)

TOOL_ROWS: tuple[tuple[str, str, int, str, str, str], ...] = (
    ("empty_database_no_semantic_release", "primary_workflow", 9, "Creates a new Artifact Tree and Corpus database shell without a Semantic Release.", "Empty database exists and remains blocked until a Semantic Release is created, attached and activated.", "Create rules, activate extraction behavior or ingest files."),
    ("empty_database_default_taxonomy_no_projections", "primary_workflow", 9, "Creates an empty database with default taxonomy but no projections.", "Database exists with taxonomy present and the Semantic Release remains blocked until projections are added.", "Create a runnable database or ingest files."),
    ("empty_database_default_taxonomy_default_projections", "primary_workflow", 9, "Creates an empty database with the complete default Semantic Release.", "Runnable empty database exists with active default taxonomy and projections.", "Customize taxonomy, customize projections or ingest files."),
    ("empty_database_default_taxonomy_custom_projections", "primary_workflow", 9, "Creates an empty database with default taxonomy and custom projections.", "Runnable database exists with default taxonomy and custom projections activated.", "Create custom taxonomy or ingest files."),
    ("empty_database_custom_taxonomy_no_projections", "primary_workflow", 9, "Creates an empty database with custom taxonomy staged while projections remain open.", "Staged database exists with custom taxonomy and a blocked Semantic Release until projections are added.", "Create a runnable database or ingest files."),
    ("empty_database_custom_taxonomy_custom_projections", "primary_workflow", 9, "Creates an empty database with custom taxonomy and custom projections.", "Runnable database exists with activated custom Semantic Release.", "Ingest files."),
    ("manual_pipeline_run", "primary_workflow", 11, "Runs Vision Pipeline ingestion on source files for an active or selected database.", "Selected database contains newly ingested data and an updated batch manifest.", "Create databases, merge databases or rebuild from artifacts."),
    ("database_merge_additive_only", "primary_workflow", 12, "Merges two or more empty or filled databases additively into a new target database.", "One merged database exists with activated Semantic Release.", "Destructively replace source databases or merge sources whose empty/filled state cannot be proven."),
    ("database_rebuild_from_artifacts", "primary_workflow", 12, "Rebuilds a Corpus database from an existing Artifact Tree and intact Semantic Release.", "One database is rebuilt from artifacts with activated Semantic Release.", "Create new rules from samples or merge multiple databases."),
    ("create_custom_taxonomy_path", "continuation_loop", 9, "Creates custom taxonomy from analyzed sample documents for a staged database or parent workflow.", "Custom taxonomy exists and can be staged into the parent Semantic Release workflow.", "Create projections or ingest files."),
    ("create_custom_projection_path", "continuation_loop", 9, "Creates custom projections against an existing or staged taxonomy.", "Custom projections exist and are valid against the taxonomy.", "Create taxonomy or ingest files."),
    ("reset_database", "continuation_loop", 11, "Resets a database into an empty state as part of Kernel-approved recovery or refinement.", "Target database is empty and ready for the planned next workflow step.", "Mean cancel, or clean up without destructive Kernel policy."),
    ("kernel_status", "support_control", 7, "Reads current Kernel and Pipeline state without changing anything.", "Current state is mirrored into Agent context and UI without mutation.", "Start, continue, cancel or modify workflows."),
    ("kernel_resume_state", "support_control", 7, "Lists Kernel workflows resumable after interruption, pending interaction, blocked execution or restart.", "Resumable workflow state and Kernel-owned resume options are mirrored into Agent context and UI.", "Execute the resumed workflow by itself."),
    ("kernel_continue_resumable_workflow", "support_control", 7, "Continues a Kernel-listed resumable workflow using an opaque resume option ref from kernel_resume_state.", "The selected resumable workflow is validated, mapped to its continuation route and continued without starting unrelated fresh work.", "Accept paths, names, database targets, raw resume-state IDs or workflow values authored by the Agent."),
    ("kernel_cancel_active_run", "support_control", 7, "Requests cancellation or pause of an active Kernel-owned workflow or Pipeline run.", "Active operation is cancelled or marked cancellation-requested when supported; no-active-run is a read-only no-op.", "Delete produced artifacts or database records."),
)


def _definition(row: tuple[str, str, int, str, str, str]) -> AgentToolDefinition:
    tool_name, layer, phase, description, outcome, does_not = row
    return AgentToolDefinition(
        tool_name=tool_name,
        visibility="permanent",
        layer=layer,
        description=description,
        outcome=outcome,
        does_not=does_not,
        implemented_by_phase=phase,
        handler_status="implemented_phase_7" if phase == 7 else f"surface_only_until_phase_{phase}",
    )


PERMANENT_AGENT_TOOL_DEFINITIONS = tuple(_definition(row) for row in TOOL_ROWS)
PERMANENT_AGENT_TOOL_NAMES = tuple(tool.tool_name for tool in PERMANENT_AGENT_TOOL_DEFINITIONS)
PERMANENT_AGENT_TOOL_MAP = {tool.tool_name: tool for tool in PERMANENT_AGENT_TOOL_DEFINITIONS}
MODEL_VISIBLE_PARAMETER_SCHEMA = empty_model_visible_schema()


def list_permanent_tools() -> tuple[AgentToolDefinition, ...]:
    return PERMANENT_AGENT_TOOL_DEFINITIONS


def get_permanent_tool(tool_name: str) -> AgentToolDefinition | None:
    return PERMANENT_AGENT_TOOL_MAP.get(tool_name)


def model_visible_parameter_schema() -> dict[str, object]:
    return empty_model_visible_schema()
