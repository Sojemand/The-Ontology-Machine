from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.batches import PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.reset_interaction_helpers import (
    _clean_path,
    _clean_text,
    _interaction_snapshot_id,
    _interaction_target_identity,
    _prefilled_values_for,
    _reset_placeholder_identity,
    _summary_for,
    _title_for,
)
from semantic_control_kernel.workflows.pipeline_run.reset_interaction_types import (
    RESET_INTERACTION_FUNCTIONS,
    _ResetInteractionProgress,
)


def progress_from_recorded_responses(
    interaction_store: InteractionRequestStore,
    workflow_run_id: str,
) -> _ResetInteractionProgress:
    artifact_root: str | None = None
    target_database_name: str | None = None
    latest_confirmation_decision: str | None = None
    records = interaction_store.list_records_for_workflow(workflow_run_id)
    records.sort(key=lambda record: str(record.created_at))
    for record in records:
        request_payload = record.interaction_request if isinstance(record.interaction_request, Mapping) else {}
        response_payload = record.get("interaction_response", {}) if isinstance(record.get("interaction_response"), Mapping) else {}
        interaction_function = str(request_payload.get("interaction_function") or "")
        if record.status != "submitted" or interaction_function not in RESET_INTERACTION_FUNCTIONS:
            continue
        if interaction_function == "choose_artifact_root_folder":
            artifact_root = _clean_path(response_payload.get("path_value"))
            continue
        if interaction_function == "name_database":
            target_database_name = _clean_text(response_payload.get("text_value"))
            continue
        if interaction_function == "user_confirmation":
            latest_confirmation_decision = _clean_text(response_payload.get("confirmation_decision"))
    return _ResetInteractionProgress(
        artifact_root=artifact_root,
        target_database_name=target_database_name,
        latest_confirmation_decision=latest_confirmation_decision,
    )


def open_next_interaction(
    user_interaction_service: KernelUserInteractionService,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    progress: _ResetInteractionProgress,
) -> None:
    interaction_function = str(progress.next_interaction_function or "choose_artifact_root_folder")
    user_interaction_service.request_interaction(
        interaction_function=interaction_function,
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=_reset_placeholder_identity(workflow_run_id),
        state_snapshot_identity={"state_snapshot_id": _interaction_snapshot_id(workflow_run_id, interaction_function)},
        user_visible_title=_title_for(interaction_function),
        user_visible_summary=_summary_for(interaction_function, progress),
        prefilled_values=_prefilled_values_for(interaction_function, progress),
    )


def open_reset_confirmation(
    user_interaction_service: KernelUserInteractionService,
    *,
    workflow_tool: str,
    workflow_run_id: str,
    target: PipelineRunTarget,
) -> None:
    user_interaction_service.request_interaction(
        interaction_function="user_confirmation",
        workflow_run_id=workflow_run_id,
        function_or_route=workflow_tool,
        target_identity=_interaction_target_identity(target),
        state_snapshot_identity={"state_snapshot_id": target.state_snapshot_id},
        user_visible_title="Confirm Database Reset",
        user_visible_summary=(
            "Confirm reset only if this exact Corpus database should be cleared while preserving its active Semantic Release."
        ),
        risk_class="destructive",
        confirmation_request_id=f"reset_database:{workflow_run_id}:{target.database_path_hash}:{target.state_snapshot_id}",
        prefilled_values={
            "target_database_path": target.database_path,
            "artifact_root": target.artifact_root_path,
            "active_release_fingerprint": target.release_fingerprint,
        },
    )
