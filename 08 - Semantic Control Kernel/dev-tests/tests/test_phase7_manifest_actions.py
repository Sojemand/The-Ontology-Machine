from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_NAMES
from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_NAMES


MODULE_ROOT = Path(__file__).resolve().parents[2]

SPEC22_ATOMIC_FUNCTION_NAMES = {
    "create_standard_artifact_folder_tree",
    "create_empty_database",
    "store_active_artifact_folder_tree",
    "write_semantic_release",
    "attach_semantic_release_to_database",
    "attach_default_semantic_release_to_database",
    "attach_custom_semantic_release_to_database",
    "activate_semantic_release",
    "remove_projection_from_database",
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
}


def test_manifest_transitions_to_agent_surface_shell() -> None:
    manifest = json.loads((MODULE_ROOT / "module-manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "agent_surface_shell"
    assert manifest["contract_version"] == 1


def test_manifest_actions_equal_permanent_agent_tools_in_order() -> None:
    manifest = json.loads((MODULE_ROOT / "module-manifest.json").read_text(encoding="utf-8"))

    assert tuple(manifest["actions"]) == PERMANENT_AGENT_TOOL_NAMES
    assert len(manifest["actions"]) == 16


def test_manifest_excludes_mcp_atomic_recovery_and_healthcheck_actions() -> None:
    manifest = json.loads((MODULE_ROOT / "module-manifest.json").read_text(encoding="utf-8"))
    actions = set(manifest["actions"])

    assert not actions.intersection(SPEC22_ATOMIC_FUNCTION_NAMES)
    assert not actions.intersection(EVENT_SCOPED_RECOVERY_TOOL_NAMES)
    assert "healthcheck" not in actions
    assert "action_catalog" not in actions
