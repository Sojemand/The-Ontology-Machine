from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from semantic_control_kernel.workflows.pipeline_run.manual_interaction_helpers import (
    clean_path,
    clean_text,
)


MANUAL_PIPELINE_INTERACTION_FUNCTIONS: tuple[str, ...] = (
    "choose_artifact_root_folder",
    "name_database",
    "select_sample_files",
    "user_confirmation",
)


@dataclass(frozen=True)
class ManualPipelineInteractionProgress:
    artifact_root: str | None = None
    target_database_name: str | None = None
    latest_input_decision: str | None = None
    latest_error_restore_decision: str | None = None

    @property
    def next_interaction_function(self) -> str | None:
        if not self.artifact_root:
            return "choose_artifact_root_folder"
        return None


def progress_from_recorded_responses(interaction_store, workflow_run_id: str) -> ManualPipelineInteractionProgress:
    artifact_root: str | None = None
    target_database_name: str | None = None
    latest_input_decision: str | None = None
    latest_error_restore_decision: str | None = None
    records = interaction_store.list_records_for_workflow(workflow_run_id)
    records.sort(key=lambda record: str(record.created_at))
    for record in records:
        request_payload = record.interaction_request if isinstance(record.interaction_request, Mapping) else {}
        response_payload = record.get("interaction_response", {}) if isinstance(record.get("interaction_response"), Mapping) else {}
        interaction_function = str(request_payload.get("interaction_function") or "")
        if record.status != "submitted" or interaction_function not in MANUAL_PIPELINE_INTERACTION_FUNCTIONS:
            continue
        if interaction_function == "choose_artifact_root_folder":
            artifact_root = clean_path(response_payload.get("path_value"))
            continue
        if interaction_function == "name_database":
            target_database_name = clean_text(response_payload.get("text_value"))
            continue
        if interaction_function == "select_sample_files":
            latest_input_decision = clean_text(response_payload.get("confirmation_decision"))
            continue
        if interaction_function == "user_confirmation":
            confirmation_request_id = str(request_payload.get("confirmation_request_id") or "")
            decision = clean_text(response_payload.get("confirmation_decision"))
            if confirmation_request_id.startswith("manual_pipeline_run.restore_error_cases:"):
                latest_error_restore_decision = decision
    return ManualPipelineInteractionProgress(
        artifact_root=artifact_root,
        target_database_name=target_database_name,
        latest_input_decision=latest_input_decision,
        latest_error_restore_decision=latest_error_restore_decision,
    )
