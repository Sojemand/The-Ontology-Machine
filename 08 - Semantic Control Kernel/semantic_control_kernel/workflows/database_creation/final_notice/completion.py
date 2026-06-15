from __future__ import annotations

from typing import TYPE_CHECKING, Any

from semantic_control_kernel.workflows.database_creation.final_notice.next_steps import (
    _no_semantic_release_next_step_options,
    _projectionless_next_step_options,
    _ready_default_release_next_step_options,
)
from semantic_control_kernel.workflows.database_creation.final_notice.payloads import (
    _completion_payload,
    _created_artifact_summary_sentence,
    _kernel_persistence,
    _outcome,
    _projectionless_outcome,
)
from semantic_control_kernel.workflows.database_creation.final_notice.completion_summaries import (
    default_ready_completion_summary,
    projectionless_cfg,
    projectionless_completion_summary,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


PATH_INSTRUCTION = {"explain_semantic_meaning": True, "explain_surface_availability": True, "include_created_artifact_paths": True}


def _empty_database_no_semantic_release_completion_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    summary = (
        "Artifact Tree and empty Corpus DB were created. No Semantic Release is attached yet. "
        f"{_created_artifact_summary_sentence(execution)} "
        "Choose next whether to attach the default Semantic Release or create a custom taxonomy and then custom projections."
    )
    return _completion_notice(
        execution,
        summary=summary,
        decision_prompt="Choose the default Semantic Release path or the custom taxonomy plus custom projections path.",
        outcome=_outcome(execution, semantic_release_attached=False, semantic_release_active=False, database_ready_for_ingest=False),
        kernel_persistence=_kernel_persistence(execution, attach_state_written=False),
        meaning="A physical Artifact Tree and empty Corpus DB exist, but no taxonomy or projections are active yet.",
        user_impact="The database is not ready for semantic extraction or ingestion until a Semantic Release path is completed.",
        next_step_options=_no_semantic_release_next_step_options(),
        guidance_goal="Explain what the Kernel created and what the user can do next.",
        guidance_style="brief_operational_summary_with_next_steps",
        guidance_must_include=[
            "artifact_tree_created",
            "empty_database_created",
            "artifact_root_path",
            "database_path",
            "semantic_release_not_attached",
            "database_not_ready_for_ingest_yet",
        ],
        next_step_instruction={**PATH_INSTRUCTION, "mention_when_database_becomes_runnable": True},
        do_not_claim=[
            "that ingestion is already possible",
            "that a semantic release is already active",
            "that attach_default_semantic_release is a direct permanent agent tool unless the surface actually exposes it",
        ],
    )


def _empty_database_default_taxonomy_default_projections_completion_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    return _completion_notice(
        execution,
        summary=default_ready_completion_summary(execution),
        decision_required=False,
        decision_prompt="No creation decision is open. The database is ready for ingest.",
        outcome=_outcome(execution, semantic_release_attached=True, semantic_release_active=True, database_ready_for_ingest=True),
        kernel_persistence=_kernel_persistence(execution, attach_state_written="dc_attach_default_release" in execution.completed_step_ids),
        meaning="The empty database has a written, attached and activated default Semantic Release.",
        user_impact="The database is runnable for Pipeline ingestion with the built-in taxonomy and default projections.",
        next_step_options=_ready_default_release_next_step_options(),
        guidance_goal="Explain that the Kernel created a ready-to-run empty database and name safe next actions.",
        guidance_style="brief_operational_summary_with_ready_state_and_next_steps",
        guidance_must_include=[
            "artifact_tree_created",
            "empty_database_created",
            "artifact_root_path",
            "database_path",
            "default_release_path",
            "semantic_release_attached",
            "semantic_release_active",
            "database_ready_for_ingest",
        ],
        next_step_instruction={**PATH_INSTRUCTION, "mention_that_ingest_is_ready": True},
        do_not_claim=[
            "that files were already ingested",
            "that taxonomy or projections were customized",
            "that taxonomy or projection modification workflow tools are available from this final notice",
        ],
    )


def _empty_database_default_taxonomy_no_projections_completion_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    return _projectionless_completion_notice(execution, custom_taxonomy=False)


def _custom_taxonomy_no_projections_completion_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    return _projectionless_completion_notice(execution, custom_taxonomy=True)


def _completion_notice(
    execution: "DatabaseCreationExecution",
    *,
    summary: str,
    decision_prompt: str,
    outcome: dict[str, Any],
    kernel_persistence: dict[str, Any],
    meaning: str,
    user_impact: str,
    next_step_options: list[dict[str, Any]],
    guidance_goal: str,
    guidance_style: str,
    guidance_must_include: list[str],
    next_step_instruction: dict[str, Any],
    do_not_claim: list[str],
    decision_required: bool = True,
) -> tuple[str, dict[str, Any]]:
    return summary, _completion_payload(
        execution,
        decision_required=decision_required,
        decision_prompt=decision_prompt,
        outcome=outcome,
        kernel_persistence=kernel_persistence,
        state_meaning={"semantic_release_state": execution.final_state, "meaning": meaning, "user_impact": user_impact},
        next_step_options=next_step_options,
        guidance_goal=guidance_goal,
        guidance_style=guidance_style,
        guidance_must_include=guidance_must_include,
        next_step_instruction=next_step_instruction,
        do_not_claim=do_not_claim,
    )


def _projectionless_completion_notice(
    execution: "DatabaseCreationExecution",
    *,
    custom_taxonomy: bool,
) -> tuple[str, dict[str, Any]]:
    cfg = projectionless_cfg(custom_taxonomy)
    return _completion_notice(
        execution,
        summary=projectionless_completion_summary(execution, custom_taxonomy=custom_taxonomy),
        decision_prompt=f"Continue through Kernel resume state to create custom projections for the {cfg['taxonomy_label']}.",
        outcome=_projectionless_outcome(execution),
        kernel_persistence=_kernel_persistence(execution, attach_state_written=False),
        meaning=str(cfg["meaning"]),
        user_impact=str(cfg["user_impact"]),
        next_step_options=_projectionless_next_step_options(taxonomy_label=str(cfg["taxonomy_label"])),
        guidance_goal=str(cfg["guidance_goal"]),
        guidance_style="brief_operational_summary_with_incomplete_semantic_state_and_next_steps",
        guidance_must_include=[
            "artifact_tree_created",
            "empty_database_created",
            "artifact_root_path",
            "database_path",
            str(cfg["stage_path_key"]),
            "taxonomy_present",
            "projections_missing",
            "database_not_ready_for_ingest_yet",
        ],
        next_step_instruction={**PATH_INSTRUCTION, "mention_that_custom_projections_are_required": True},
        do_not_claim=list(cfg["do_not_claim"]),
    )
