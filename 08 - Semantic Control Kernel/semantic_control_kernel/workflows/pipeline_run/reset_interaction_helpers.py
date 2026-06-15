from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.batches import PipelineRunBlocker, PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.reset_interaction_types import _ResetInteractionProgress


def _reset_placeholder_identity(workflow_run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "state.target_identity.v1",
        "artifact_root_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:reset_artifact_root')}",
        "database_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:reset_database')}",
        "target_hash": stable_hash(f"{workflow_run_id}:reset_target"),
        "lock_scope": "database_reset",
        "workflow_run_id": workflow_run_id,
        "created_from": "kernel.database_reset_target_collection.v1",
    }


def _interaction_target_identity(target: PipelineRunTarget) -> dict[str, Any]:
    return {key: value for key, value in target.target_identity.items() if key != "state_snapshot_id"}


def _interaction_snapshot_id(workflow_run_id: str, interaction_function: str) -> str:
    return stable_hash(f"{workflow_run_id}:{interaction_function}")


def _title_for(interaction_function: str) -> str:
    if interaction_function == "choose_artifact_root_folder":
        return "Choose Reset Artifact Tree"
    return "Name Database To Reset"


def _summary_for(interaction_function: str, progress: _ResetInteractionProgress) -> str:
    if interaction_function == "choose_artifact_root_folder":
        return "Choose the Artifact Tree that contains the Corpus database to reset."
    if progress.artifact_root:
        return f"Enter the Corpus database name to reset inside {Path(progress.artifact_root).name}."
    return "Enter the Corpus database name to reset from the selected Artifact Tree."


def _prefilled_values_for(interaction_function: str, progress: _ResetInteractionProgress) -> dict[str, Any]:
    if interaction_function == "name_database" and progress.artifact_root:
        return {"text_value": Path(progress.artifact_root).name}
    return {}


def _input_blocker(summary: str) -> PipelineRunBlocker:
    return PipelineRunBlocker(
        blocker_code="input_missing",
        step_id="reset_collect_interaction",
        function_or_route="reset_database",
        recovery_state_class="expired_pending_interaction",
        user_visible_summary=summary,
    )


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _clean_path(value: object) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
        if not text:
            return None
    return str(Path(text).resolve(strict=False))
