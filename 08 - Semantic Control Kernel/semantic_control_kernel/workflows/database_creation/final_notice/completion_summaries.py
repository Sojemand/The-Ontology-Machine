from __future__ import annotations

from typing import TYPE_CHECKING

from semantic_control_kernel.workflows.database_creation.final_notice.payloads import (
    _already_available_sentence_part,
    _created_artifact_summary_sentence,
    _workflow_explanation_context,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def default_ready_completion_summary(execution: "DatabaseCreationExecution") -> str:
    reused = _workflow_explanation_context(execution).get("already_available")
    paths = _created_artifact_summary_sentence(execution, include_default_release=True, prefix="Paths" if reused else "Created paths")
    if reused:
        return (
            f"Previously available workflow state was reused: {_already_available_sentence_part(_workflow_explanation_context(execution))}. "
            f"Default Semantic Release was exported, written, attached and activated. {paths} "
            "The Semantic Release is active, so the database is ready for ingest."
        )
    return f"Artifact Tree, empty Corpus DB and the complete default Semantic Release were created. {paths} The Semantic Release is active, so the database is ready for ingest."


def projectionless_completion_summary(execution: "DatabaseCreationExecution", *, custom_taxonomy: bool) -> str:
    context = _workflow_explanation_context(execution)
    reused = context.get("already_available")
    cfg = projectionless_cfg(custom_taxonomy)
    paths = _created_artifact_summary_sentence(
        execution,
        include_default_release=not custom_taxonomy,
        include_projectionless_state=not custom_taxonomy,
        include_custom_taxonomy_stage=custom_taxonomy,
        prefix="Paths" if reused else "Created paths",
    )
    if reused:
        return (
            f"Previously available workflow state was reused: {_already_available_sentence_part(context)}. "
            f"{cfg['reused_action']} {paths} Projections are missing, so the database is not ready for ingest until custom projections are added."
        )
    return f"Artifact Tree, empty Corpus DB and {cfg['created_object']} were created. {paths} Projections are missing, so the database is not ready for ingest until custom projections are added."


def projectionless_cfg(custom_taxonomy: bool) -> dict[str, object]:
    if custom_taxonomy:
        return {
            "taxonomy_label": "staged custom taxonomy",
            "stage_path_key": "custom_taxonomy_stage_path",
            "guidance_goal": "Explain that the Kernel created a custom-taxonomy database that still needs projections.",
            "meaning": "The database has a staged custom taxonomy, but no projections and no runnable Semantic Release are active.",
            "user_impact": "The custom taxonomy can be used for governed projection authoring. Pipeline ingest must wait for custom projections and activation.",
            "created_object": "a staged custom taxonomy",
            "reused_action": "Custom taxonomy was authored and staged for custom projection authoring.",
            "do_not_claim": [
                "that ingestion is already possible",
                "that a complete custom Semantic Release has already been written",
                "that create_custom_projection_path can bypass Kernel resume selection",
            ],
        }
    return {
        "taxonomy_label": "staged default taxonomy",
        "stage_path_key": "projectionless_release_state_path",
        "guidance_goal": "Explain that the Kernel created a taxonomy-present database that still needs projections.",
        "meaning": "The database has default taxonomy proof persisted as projectionless release state, but no runnable Semantic Release is active.",
        "user_impact": "The taxonomy vocabulary can be used for governed projection authoring. Pipeline ingest must wait for custom projections and activation.",
        "created_object": "the default taxonomy-only Semantic Release state",
        "reused_action": "Default taxonomy was staged and default projections were removed for custom projection authoring.",
        "do_not_claim": [
            "that ingestion is already possible",
            "that default projections remain attached",
            "that create_custom_projection_path can bypass Kernel resume selection",
        ],
    }
