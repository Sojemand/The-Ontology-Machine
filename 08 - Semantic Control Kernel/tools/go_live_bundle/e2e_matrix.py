from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_DEFINITIONS

from .paths import MODULE_ROOT, _write_json


def _write_e2e_matrix(bundle_root: Path, run_id: str, fixture_root: Path) -> None:
    entries = [
        _e2e("Creation 1", ["empty_database_no_semantic_release"], "Artifact Tree and DB shell are created; final state is blocked by missing Semantic Release; resume can continue into release creation."),
        _e2e("Creation 2", ["empty_database_default_taxonomy_no_projections"], "Default taxonomy is staged; missing projections blocker is user-visible and resumable."),
        _e2e("Creation 3", ["empty_database_default_taxonomy_default_projections"], "Default Semantic Release is written, attached and activated; no sample ingestion occurs."),
        _e2e("Creation 4", ["empty_database_default_taxonomy_custom_projections", "create_custom_projection_path"], "Custom projection route runs through fake LLM, update-state artifact, owner materialization and activation."),
        _e2e("Creation 5", ["empty_database_custom_taxonomy_no_projections", "create_custom_taxonomy_path"], "Custom taxonomy is materialized; projections remain missing; staged work is resumable."),
        _e2e("Creation 6", ["empty_database_custom_taxonomy_custom_projections", "create_custom_taxonomy_path", "create_custom_projection_path"], "Custom taxonomy and projections are materialized, validated together, written and activated."),
        _e2e("Manual pipeline run", ["manual_pipeline_run"], "Active Semantic Release is required; batch manifest is created/finalized; progress events show stages."),
        _e2e("Reset database", ["reset_database"], "Destructive confirmation is required and release relationship is preserved or blocked explicitly."),
        _e2e("Empty merge", ["database_merge_additive_only"], "Multi-source empty merge uses the canonical merge service and not pairwise legacy chaining; empty routing is Kernel-internal."),
        _e2e("Filled merge", ["database_merge_additive_only"], "SQL IDs, artifact paths, batch IDs, embedding refs and materialization refs are remapped; filled routing is Kernel-internal."),
        _e2e("Support and recovery", ["kernel_status", "kernel_resume_state", "kernel_cancel_active_run"], "Support tools stay permanent while recovery tools remain event-scoped and receipt-backed."),
    ]
    payload = {
        "schema_version": "semantic_control_kernel.phase20.e2e_fixture_matrix.v1",
        "go_live_run_id": run_id,
        "realistic_corpus_path": fixture_root.relative_to(MODULE_ROOT).as_posix(),
        "permanent_tool_coverage": [definition.tool_name for definition in PERMANENT_AGENT_TOOL_DEFINITIONS],
        "recovery_state_coverage": [
            "stale_lock",
            "target_identity_changed",
            "broken_database_artifact_binding",
            "semantic_release_incomplete_staged",
            "partial_pipeline_run",
            "unresolved_merge_collision",
            "missing_manifest_or_originals",
            "final_llm_validation_failure",
            "expired_pending_interaction",
            "support_only_unrecoverable",
        ],
        "entries": entries,
    }
    _write_json(bundle_root / "e2e_matrix" / "e2e_fixture_matrix.json", payload)
    (bundle_root / "e2e_matrix" / "README.md").write_text(
        "# E2E Matrix\n\nStructured source: `e2e_fixture_matrix.json`.\n",
        encoding="utf-8",
    )


def _e2e(area: str, tools: list[str], proof: str) -> dict[str, Any]:
    return {
        "matrix_area": area,
        "covered_tools": tools,
        "must_prove": proof,
    }
