from __future__ import annotations

from pathlib import Path

import pytest

from semantic_control_kernel.repository.errors import StatePathEscapeError
from semantic_control_kernel.repository.paths import StatePaths


DRIFT_PREFLIGHT = {
    "status": "drift_preflight: build_plan_authority_applied",
    "details": [
        {
            "documents": [
                "Semantic Kernel SPEC/01_kernel_scope_state_terminology.md",
                "Semantic Kernel SPEC/02_kernel_state_transition_table.md",
                "Semantic Kernel SPEC/08_user_function_surface.md",
                "Semantic Kernel SPEC/10_kernel_only_functions.md",
                "Semantic Kernel SPEC/11_kernel_internal_data_contracts.md",
                "Semantic Kernel SPEC/12_shared_llm_contract_rules.md",
                "Semantic Kernel SPEC/22_mcp_kernel_pipeline_function_contract.md",
                "Semantic Kernel SPEC/23_agent_facing_pipeline_manager_tools.md",
            ],
            "reason": "Referenced specs define Kernel truth boundaries and contract rows, but omit the Phase 3 resolved repository-local state layout, local schemas, atomic write mechanics and reset archive behavior.",
        }
    ],
}


SPEC_EXPECTED_LAYOUT = {
    ".fs_locks",
    ".tmp",
    "README.md",
    "archive",
    "archive/resets",
    "adapter_calls",
    "artifact_trees",
    "artifact_trees/active",
    "artifact_trees/history",
    "attach_states",
    "attach_states/by_database",
    "attach_states/history",
    "bindings",
    "bindings/history",
    "bindings/index",
    "bindings/index/by_artifact_root",
    "bindings/index/by_database_path",
    "bindings/records",
    "debug",
    "debug/adapter_calls",
    "debug/background_continuations",
    "debug/llm_attempts",
    "debug/redaction_reports",
    "debug/traces",
    "events",
    "events/mirror",
    "events/progress",
    "events/recovery",
    "events/tool_availability",
    "locks",
    "locks/active",
    "locks/history",
    "pending_confirmations",
    "pending_confirmations/active",
    "pending_confirmations/history",
    "pending_interactions",
    "pending_interactions/active",
    "pending_interactions/history",
    "quarantine",
    "quarantine/corrupt",
    "quarantine/partial_writes",
    "receipts",
    "receipts/confirmations",
    "receipts/index",
    "receipts/index/by_target",
    "receipts/index/by_workflow",
    "receipts/operations",
    "receipts/recoveries",
    "resume",
    "state_root_manifest.json",
    "support",
    "support/bundles",
    "support/cleanup_history",
    "support/index.json",
    "workflow_runs",
    "workflow_runs/active",
    "workflow_runs/history",
}


def test_drift_preflight_recorded_for_phase3() -> None:
    assert DRIFT_PREFLIGHT["status"] == "drift_preflight: build_plan_authority_applied"
    assert DRIFT_PREFLIGHT["details"]


def test_state_paths_create_exact_phase3_layout(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()

    actual = {
        path.relative_to(paths.state_root).as_posix()
        for path in paths.state_root.rglob("*")
        if path != paths.state_root
    }

    assert actual == SPEC_EXPECTED_LAYOUT
    assert paths.expected_layout_entries() == SPEC_EXPECTED_LAYOUT


def test_state_paths_remain_under_configured_root(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()

    lock_path = paths.safe_path("locks", "active", "example.json")

    assert lock_path.is_relative_to(paths.state_root)


def test_state_paths_reject_path_traversal_and_absolute_escape(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()

    with pytest.raises(StatePathEscapeError):
        paths.safe_path("..", "outside.json")

    with pytest.raises(StatePathEscapeError):
        paths.safe_path(str(tmp_path / "outside.json"))
