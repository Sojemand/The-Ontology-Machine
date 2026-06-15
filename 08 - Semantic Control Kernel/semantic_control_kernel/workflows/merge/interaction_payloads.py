from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import StatePaths, path_hash, stable_hash
from semantic_control_kernel.types.merge import (
    PROJECTION_MERGE_MODE_PRESERVE,
    PROJECTION_MERGE_MODE_SINGLE,
    MergeWorkflowBlocker,
)
from semantic_control_kernel.workflows.merge.source_registry import list_merge_database_options


def merge_placeholder_identity(workflow_run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "state.target_identity.v1",
        "source_database_set_hash": f"pending:{stable_hash(f'{workflow_run_id}:source_set')}",
        "database_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:database')}",
        "artifact_root_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:artifact_root')}",
        "target_hash": stable_hash(f"{workflow_run_id}:merge_interaction"),
        "lock_scope": "merge",
        "workflow_run_id": workflow_run_id,
        "created_from": "kernel.database_merge_interaction.v1",
    }


def merge_target_identity(
    workflow_run_id: str,
    selected_sources: Sequence[Mapping[str, Any]],
    target_artifact_root: str,
) -> dict[str, Any]:
    target_database_path = str(Path(target_artifact_root) / "Corpus" / "corpus.db")
    source_ids = sorted(
        str(
            source.get("durable_source_database_id")
            or source.get("source_database_id")
            or source.get("source_database_path")
            or ""
        )
        for source in selected_sources
    )
    source_hash = stable_hash("|".join(source_ids))
    artifact_hash = path_hash(target_artifact_root)
    database_hash = path_hash(target_database_path)
    return {
        "schema_version": "state.target_identity.v1",
        "source_database_set_hash": source_hash,
        "database_path_hash": database_hash,
        "artifact_root_path_hash": artifact_hash,
        "target_hash": stable_hash(f"{artifact_hash}:{database_hash}:{source_hash}:{workflow_run_id}"),
        "lock_scope": "merge",
        "workflow_run_id": workflow_run_id,
        "created_from": "kernel.database_merge_interaction.v1",
    }


def interaction_snapshot_id(workflow_run_id: str, interaction_function: str) -> str:
    return stable_hash(f"{workflow_run_id}:{interaction_function}")


def title_for(interaction_function: str) -> str:
    if interaction_function == "choose_merge_database_count":
        return "How Many Databases To Merge"
    if interaction_function == "choose_databases_to_merge":
        return "Enter Source Artifact Tree Paths"
    if interaction_function == "choose_merge_projection_mode":
        return "Choose Projection Merge Mode"
    return "Choose New Artifact Root Folder"


def summary_for(interaction_function: str, selected_database_count: int) -> str:
    if interaction_function == "choose_merge_database_count":
        return "Enter the number of source databases to merge. Minimum is 2."
    if interaction_function == "choose_databases_to_merge":
        return f"Enter {selected_database_count} source Artifact Tree root paths. The Kernel resolves each Corpus DB and release from the selected Artifact Trees."
    if interaction_function == "choose_merge_projection_mode":
        return "Choose whether the target release keeps source projections side by side or compiles them into one merged projection. Single-projection merge is available only for empty source databases."
    return f"Choose the new target Artifact Tree root for the additive merge of {selected_database_count} source databases."


def options_for(state_paths: StatePaths, interaction_function: str) -> list[dict[str, Any]] | None:
    if interaction_function == "choose_databases_to_merge":
        return list_merge_database_options(state_paths)
    if interaction_function == "choose_merge_projection_mode":
        return [
            {
                "choice_id": PROJECTION_MERGE_MODE_PRESERVE,
                "label": "Keep source projections",
                "description": "Preserve current behavior: merged release keeps the selected source projections side by side.",
            },
            {
                "choice_id": PROJECTION_MERGE_MODE_SINGLE,
                "label": "Merge into one projection",
                "description": "Compile source projections into one target projection. Empty database merges only.",
            },
        ]
    return None


def prefilled_values_for(
    interaction_function: str,
    selected_database_paths: Sequence[str],
    *,
    source_count: int = 0,
) -> dict[str, Any]:
    if interaction_function == "choose_merge_database_count":
        return {}
    if interaction_function == "choose_databases_to_merge":
        return {
            "manual_path_count": source_count,
            "path_value_kind": "artifact_tree_root",
            "selected_database_paths": list(selected_database_paths),
        }
    if interaction_function == "choose_new_artifact_root_folder":
        source_hash = stable_hash("|".join(sorted(path_hash(path) for path in selected_database_paths)))
        return {"source_database_count": len(selected_database_paths), "source_database_set_hash": source_hash}
    if interaction_function == "choose_merge_projection_mode":
        return {"choice_id": PROJECTION_MERGE_MODE_PRESERVE}
    return {}


def clean_database_paths(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        path = clean_path(item)
        if path is None:
            continue
        key = path_hash(path)
        if key not in seen:
            cleaned.append(path)
            seen.add(key)
    return tuple(cleaned)


def clean_path(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    return str(Path(text).resolve(strict=False)) if text else None


def source_resolution_blocker(summary: str) -> MergeWorkflowBlocker:
    return MergeWorkflowBlocker(
        "binding_missing",
        "merge_collect_sources",
        "database_merge_additive_only",
        "broken_database_artifact_binding",
        summary,
    )


def target_resolution_blocker(summary: str) -> MergeWorkflowBlocker:
    return MergeWorkflowBlocker(
        "invalid_target_path",
        "merge_collect_target",
        "database_merge_additive_only",
        "target_identity_changed",
        summary,
    )
