from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import path_hash, stable_hash
from semantic_control_kernel.types.database_creation import DatabaseCreationTarget

CREATION_TARGET_INTERACTION_FUNCTIONS: tuple[str, ...] = (
    "choose_artifact_root_folder",
    "name_artifact_root_folder",
    "name_database",
)
SAMPLE_FILE_INTERACTION_FUNCTION = "select_sample_files"


@dataclass(frozen=True)
class CreationTargetProgress:
    artifact_root_parent_path: str | None = None
    artifact_root_path: str | None = None
    database_name: str | None = None

    @property
    def next_interaction_function(self) -> str | None:
        if not self.artifact_root_parent_path:
            return "choose_artifact_root_folder"
        if not self.artifact_root_path:
            return "name_artifact_root_folder"
        if not self.database_name:
            return "name_database"
        return None


def creation_target_progress_from_records(records: list[Any]) -> CreationTargetProgress:
    choose_path: str | None = None
    artifact_root_path: str | None = None
    database_name: str | None = None
    records.sort(key=lambda record: str(record.created_at))
    for record in records:
        request_payload = record.interaction_request if isinstance(record.interaction_request, Mapping) else {}
        response_payload = record.get("interaction_response", {}) if isinstance(record.get("interaction_response"), Mapping) else {}
        interaction_function = str(request_payload.get("interaction_function") or "")
        if record.status != "submitted" or interaction_function not in CREATION_TARGET_INTERACTION_FUNCTIONS:
            continue
        if interaction_function == "choose_artifact_root_folder":
            choose_path = clean_path(response_payload.get("path_value"))
        elif interaction_function == "name_artifact_root_folder":
            artifact_root_path = artifact_root_path_from_response(response_payload, choose_path)
        elif interaction_function == "name_database":
            database_name = clean_text(response_payload.get("text_value"))
    return CreationTargetProgress(
        artifact_root_parent_path=choose_path,
        artifact_root_path=artifact_root_path,
        database_name=database_name,
    )


def creation_target_placeholder_identity(workflow_run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "state.target_identity.v1",
        "artifact_root_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:artifact_root')}",
        "database_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:database')}",
        "target_hash": stable_hash(f"{workflow_run_id}:creation_target"),
        "lock_scope": "database_creation",
        "workflow_run_id": workflow_run_id,
        "created_from": "kernel.database_creation_target_collection.v1",
    }


def interaction_snapshot_id(workflow_run_id: str, interaction_function: str) -> str:
    return stable_hash(f"{workflow_run_id}:{interaction_function}")


def sample_target_identity(target: DatabaseCreationTarget) -> dict[str, Any]:
    identity = dict(target.target_identity)
    identity["input_path_hash"] = target.path_hashes.get("input_path_hash") or path_hash(target.input_path)
    return identity


def title_for(interaction_function: str) -> str:
    if interaction_function == "choose_artifact_root_folder":
        return "Choose Artifact Root Folder"
    if interaction_function == "name_artifact_root_folder":
        return "Name Artifact Root Folder"
    return "Name Database"


def summary_for(interaction_function: str, progress: CreationTargetProgress) -> str:
    if interaction_function == "choose_artifact_root_folder":
        return "Choose the parent folder for the new Artifact Tree."
    if interaction_function == "name_artifact_root_folder":
        return "Enter the name for the new Artifact Tree root folder."
    if progress.artifact_root_path:
        return f"Enter the database name for {Path(progress.artifact_root_path).name}."
    return "Enter the database name for the new Corpus database."


def prefilled_values_for(interaction_function: str, progress: CreationTargetProgress) -> dict[str, Any]:
    if interaction_function == "name_artifact_root_folder" and progress.artifact_root_parent_path:
        return {"text_value": "Artifact Tree"}
    if interaction_function == "name_database" and progress.artifact_root_path:
        return {"text_value": Path(progress.artifact_root_path).name}
    return {}


def clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def clean_path(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
        if not text:
            return None
    return str(Path(text).resolve(strict=False))


def artifact_root_path_from_response(response_payload: Mapping[str, Any], chosen_parent_path: str | None) -> str | None:
    path_value = clean_path(response_payload.get("path_value"))
    if path_value is not None:
        return path_value
    text_value = clean_text(response_payload.get("text_value"))
    if text_value is None:
        return None
    if chosen_parent_path is not None:
        return str((Path(chosen_parent_path) / text_value).resolve(strict=False))
    return str(Path(text_value).resolve(strict=False))
