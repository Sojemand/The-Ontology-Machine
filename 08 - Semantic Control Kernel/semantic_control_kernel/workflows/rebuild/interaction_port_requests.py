from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.workflows.rebuild.interaction_port_identity import (
    interaction_snapshot_id,
    rebuild_placeholder_identity,
)
from semantic_control_kernel.workflows.rebuild.interaction_port_state import RebuildInteractionProgress


def open_next_interaction(
    user_interaction_service: KernelUserInteractionService,
    workflow_tool: str,
    workflow_run_id: str,
    progress: RebuildInteractionProgress,
) -> None:
    interaction_function = str(progress.next_interaction_function or "choose_artifact_root_folder")
    user_interaction_service.request_interaction(
        interaction_function=interaction_function,
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=rebuild_placeholder_identity(workflow_run_id),
        state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, interaction_function)},
        user_visible_title=_title_for(interaction_function),
        user_visible_summary=_summary_for(interaction_function, progress),
        prefilled_values=_prefilled_values_for(interaction_function, progress),
    )


def open_overwrite_confirmation(
    user_interaction_service: KernelUserInteractionService,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    artifact_root: str,
    target_database_path: Path,
    loaded_release: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> None:
    release_fingerprint = str(loaded_release["loaded_release_fingerprint"])
    user_interaction_service.request_interaction(
        interaction_function="user_confirmation",
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=target_identity,
        state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, "rebuild_overwrite")},
        user_visible_title="Confirm Rebuild Overwrite",
        user_visible_summary=(
            "The selected rebuild target database already exists. Confirm overwrite only if this exact "
            f"database should be rebuilt from the selected Artifact Tree and Semantic Release {release_fingerprint}."
        ),
        risk_class="destructive",
        confirmation_request_id=f"rebuild_overwrite:{workflow_run_id}:{stable_hash(str(target_database_path) + release_fingerprint)}",
        prefilled_values={
            "artifact_root": artifact_root,
            "target_database_path": str(target_database_path),
            "loaded_release_fingerprint": release_fingerprint,
            "loaded_release_path": str(loaded_release.get("loaded_release_path") or ""),
        },
    )


def open_existing_database_warning(
    user_interaction_service: KernelUserInteractionService,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    target_database_path: Path,
    existing_database_paths: tuple[Path, ...],
    target_identity: Mapping[str, Any],
) -> None:
    existing_names = ", ".join(path.name for path in existing_database_paths)
    user_interaction_service.request_interaction(
        interaction_function="user_confirmation",
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=target_identity,
        state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, "rebuild_existing_corpus_db_warning")},
        user_visible_title="Existing Corpus Database Found",
        user_visible_summary=(
            "The selected Artifact Tree Corpus folder already contains "
            f"{existing_names}. The requested rebuild target is {target_database_path.name}, "
            "which would create a separate database file instead of overwriting the existing one. Confirm to continue with this separate target."
        ),
        risk_class="non_destructive",
        confirmation_request_id=f"rebuild_existing_corpus_db_warning:{workflow_run_id}:{stable_hash(str(target_database_path) + existing_names)}",
        prefilled_values={
            "target_database_path": str(target_database_path),
            "existing_database_paths": [str(path) for path in existing_database_paths],
        },
    )


def _title_for(interaction_function: str) -> str:
    if interaction_function == "choose_artifact_root_folder":
        return "Choose Rebuild Artifact Tree"
    return "Name Rebuilt Database"


def _summary_for(interaction_function: str, progress: RebuildInteractionProgress) -> str:
    if interaction_function == "choose_artifact_root_folder":
        return "Choose the existing Artifact Tree whose Semantic Release and artifacts should rebuild a Corpus database."
    if progress.artifact_root:
        return f"Enter the Corpus database name to rebuild inside {Path(progress.artifact_root).name}."
    return "Enter the Corpus database name to rebuild from the selected Artifact Tree."


def _prefilled_values_for(interaction_function: str, progress: RebuildInteractionProgress) -> dict[str, Any]:
    if interaction_function == "name_database" and progress.artifact_root:
        return {"text_value": Path(progress.artifact_root).name}
    return {}


__all__ = [
    "open_existing_database_warning",
    "open_next_interaction",
    "open_overwrite_confirmation",
]
