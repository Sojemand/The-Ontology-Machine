from __future__ import annotations

from phase9_creation_route_expectations import EXPECTED, FROZEN_CREATION_GOLDEN, FROZEN_CREATION_TOOLS
from semantic_control_kernel.workflows.database_creation.route_sequences import (
    DRIFT_PREFLIGHT,
    KERNEL_BOOKKEEPING,
    READ_BUILD_SOURCE_STEP,
    ROUTES,
    STEP_BY_ID,
    WORKFLOW_ENTRIES,
    route_sequence,
)


def test_exact_phase9_route_sequences() -> None:
    assert DRIFT_PREFLIGHT["status"] == "drift_preflight: build_plan_authority_applied"
    assert FROZEN_CREATION_GOLDEN["schema_version"] == "kernel.phase9.frozen_primary_creation_workflows.v1"
    assert FROZEN_CREATION_TOOLS == tuple(EXPECTED)[:6]
    assert tuple(EXPECTED) == WORKFLOW_ENTRIES
    for workflow_tool, expected in EXPECTED.items():
        assert route_sequence(workflow_tool) == expected


def test_optional_continuation_steps_are_before_final_notice() -> None:
    assert route_sequence("create_custom_taxonomy_path", include_optional=True) == (
        "tax_require_samples",
        "tax_analyze_samples",
        "tax_create_proposal",
        "tax_build_update_state",
        "tax_create_custom_taxonomy",
        "tax_stage_custom_taxonomy",
        "rel_persist_incomplete_state",
        "dc_final_notice",
    )
    assert route_sequence("create_custom_projection_path", include_optional=True)[-2:] == (
        "rel_activate_custom_release",
        "dc_final_notice",
    )


def test_mutating_steps_reference_transition_rules_or_kernel_bookkeeping() -> None:
    for route in ROUTES:
        for step_id in route.sequence(include_optional=True):
            step = STEP_BY_ID[step_id]
            mutates_pipeline_or_kernel_state = step.transition_rule.startswith("tr_") or step.transition_rule in {
                KERNEL_BOOKKEEPING,
                READ_BUILD_SOURCE_STEP,
            }
            if step.adapter_or_port.startswith(("WorkspaceAdapter", "CorpusAdapter", "SemanticReleaseAdapter", "Kernel repository")):
                assert mutates_pipeline_or_kernel_state, (route.workflow_tool, step_id, step.transition_rule)


def test_write_attach_activate_are_separate_steps() -> None:
    for route in ROUTES:
        for step_id in route.sequence(include_optional=True):
            operation = STEP_BY_ID[step_id].operation
            assert not ("write_semantic_release" in operation and "attach" in operation)
            assert not ("write_semantic_release" in operation and "activate" in operation)
            assert not ("attach_" in operation and "activate_semantic_release" in operation)
