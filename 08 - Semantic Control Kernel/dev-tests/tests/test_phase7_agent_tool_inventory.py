from __future__ import annotations

from semantic_control_kernel.surface import agent_tools
from semantic_control_kernel.surface.event_scoped_tools import list_event_scoped_recovery_tool_definitions


EXPECTED_PERMANENT_NAMES = (
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

EXPECTED_RECOVERY_NAMES = (
    "kernel_apply_recovery_option",
    "kernel_open_recovery_dialog",
    "kernel_retry_recoverable_workflow",
    "kernel_resolve_stale_lock",
    "kernel_rebind_database_artifact_tree",
    "kernel_discard_or_archive_staged_work",
    "kernel_reconcile_partial_pipeline_run",
    "kernel_open_support_bundle",
)

DRIFT_PREFLIGHT = {
    "status": "drift_preflight: build_plan_authority_applied",
    "details": (
        "11_kernel_internal_data_contracts.md omits Phase 7 local agent_tool_* contracts; build plan defines them.",
        "23_agent_facing_pipeline_manager_tools.md contains fuller prose; Phase 7 compact descriptions are the surface contract.",
    ),
}


def test_drift_preflight_records_build_plan_authority() -> None:
    assert DRIFT_PREFLIGHT["status"] == "drift_preflight: build_plan_authority_applied"
    assert len(DRIFT_PREFLIGHT["details"]) == 2


def test_permanent_agent_tool_names_are_exact_and_ordered() -> None:
    tools = agent_tools.list_permanent_tools()

    assert tuple(tool.tool_name for tool in tools) == EXPECTED_PERMANENT_NAMES
    assert len(tools) == 16


def test_context_preamble_preserves_required_agent_routing_context() -> None:
    preamble = agent_tools.AGENT_SURFACE_CONTEXT_PREAMBLE
    required_fragments = (
        "source documents",
        "Corpus database",
        "Artifact Tree",
        "Semantic Release contains taxonomy and projections",
        "Empty and filled databases use different workflow safety policy",
        "Batch manifests make manual ingestion auditable",
        "workflow execution, state validation, dialogs, blockers, confirmations",
        "resume state and adapter calls",
        "Agent chooses only the workflow tool",
        "does not collect Kernel-required values",
    )

    for fragment in required_fragments:
        assert fragment in preamble


def test_event_scoped_recovery_names_are_defined_but_not_permanent() -> None:
    permanent = set(agent_tools.PERMANENT_AGENT_TOOL_NAMES)
    recovery = tuple(tool.tool_name for tool in list_event_scoped_recovery_tool_definitions())

    assert recovery == EXPECTED_RECOVERY_NAMES
    assert len(recovery) == 8
    assert not permanent.intersection(recovery)


def test_merge_route_names_are_kernel_internal_not_permanent() -> None:
    permanent = set(agent_tools.PERMANENT_AGENT_TOOL_NAMES)

    assert "database_merge_additive_only" in permanent
    assert "empty_databases_merge_path" not in permanent
    assert "filled_databases_merge_path" not in permanent


def test_every_permanent_tool_has_phase7_definition_fields() -> None:
    required = {
        "schema_version",
        "tool_name",
        "visibility",
        "layer",
        "description",
        "outcome",
        "does_not",
        "implemented_by_phase",
    }

    for definition in agent_tools.list_permanent_tools():
        payload = definition.to_dict()
        assert required.issubset(payload)
        assert payload["schema_version"] == "agent_tool_definition.v1"
        assert payload["visibility"] == "permanent"
        assert payload["description"]
        assert payload["outcome"]
        assert payload["does_not"]
