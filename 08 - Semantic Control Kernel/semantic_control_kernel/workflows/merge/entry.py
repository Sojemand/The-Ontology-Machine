from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.types.merge import PROJECTION_MERGE_MODE_DEFAULT, MergeWorkflowExecution
from semantic_control_kernel.workflows.merge.empty_merge import empty_databases_merge_path
from semantic_control_kernel.workflows.merge.filled_merge import filled_databases_merge_path
from semantic_control_kernel.workflows.merge.receipts import block_execution, blocker_from_adapter_result, start_step
from semantic_control_kernel.workflows.merge.source_selection import (
    build_database_merge_selection,
    projection_merge_mode_blocker,
    resume_database_merge_selection,
    route_blocker_for_selection,
    target_confirmation_blocker,
)


@dataclass
class MergeWorkflowRuntime:
    state_root: str | Path
    workspace_adapter: Any
    corpus_adapter: Any
    semantic_release_adapter: Any
    merge_adapter: Any
    interaction_port: Any | None = None


def database_merge_additive_only(
    *,
    runtime: MergeWorkflowRuntime,
    selected_sources: Sequence[Mapping[str, Any]],
    target_artifact_root: str | Path,
    selected_by_interaction_id: str = "interaction_phase12_merge",
    target_database_path: str | Path | None = None,
    workflow_run_id: str | None = None,
    merge_run_id: str | None = None,
    projection_merge_mode: str = PROJECTION_MERGE_MODE_DEFAULT,
    reconciliation_receipt: Mapping[str, Any] | None = None,
    target_confirmation_receipt: Mapping[str, Any] | None = None,
) -> MergeWorkflowExecution:
    resolved_workflow_run_id = workflow_run_id or generate_id("workflow_run_id")
    resolved_merge_run_id = require_state_id("merge_run_id", merge_run_id) if merge_run_id else None
    existing_selection_reused = False
    selection_or_blocker = None
    if resolved_merge_run_id:
        try:
            selection_or_blocker = resume_database_merge_selection(
                selected_sources=selected_sources,
                target_artifact_root=target_artifact_root,
                target_database_path=target_database_path,
                selected_by_interaction_id=selected_by_interaction_id,
                merge_run_id=resolved_merge_run_id,
                projection_merge_mode=projection_merge_mode,
            )
        except ValueError as exc:
            from semantic_control_kernel.types.merge import MergeWorkflowBlocker

            selection_or_blocker = MergeWorkflowBlocker(
                blocker_code="target_identity_changed",
                step_id="classifying_merge_route",
                function_or_route="database_merge_additive_only",
                recovery_state_class="target_identity_changed",
                user_visible_summary="Persisted merge selection is stale and the merge must be reselected.",
                diagnostics=({"reason": str(exc)},),
            )
        existing_selection_reused = hasattr(selection_or_blocker, "to_dict") and getattr(selection_or_blocker, "SCHEMA_VERSION", "") == "kernel.database_merge_selection.v1"
    if selection_or_blocker is None:
        selection_or_blocker = build_database_merge_selection(
            selected_sources=selected_sources,
            target_artifact_root=target_artifact_root,
            target_database_path=target_database_path,
            selected_by_interaction_id=selected_by_interaction_id,
            merge_run_id=resolved_merge_run_id,
            projection_merge_mode=projection_merge_mode,
        )
    execution = MergeWorkflowExecution(
        workflow_run_id=resolved_workflow_run_id,
        workflow_tool="database_merge_additive_only",
        merge_run_id=resolved_merge_run_id or (selection_or_blocker.to_dict()["merge_run_id"] if hasattr(selection_or_blocker, "to_dict") and "merge_run_id" in selection_or_blocker.to_dict() else generate_id("merge_run_id")),
        state_root=Path(runtime.state_root),
    )
    if not hasattr(selection_or_blocker, "to_dict") or getattr(selection_or_blocker, "SCHEMA_VERSION", "") != "kernel.database_merge_selection.v1":
        block_execution(execution, selection_or_blocker)  # type: ignore[arg-type]
        return execution
    selection = selection_or_blocker.to_dict()
    execution.merge_run_id = str(selection["merge_run_id"])
    execution.selection = selection
    blocker = route_blocker_for_selection(selection)
    if blocker is not None:
        block_execution(execution, blocker)
        return execution
    blocker = projection_merge_mode_blocker(selection)
    if blocker is not None:
        block_execution(execution, blocker)
        return execution
    blocker = target_confirmation_blocker(
        selection,
        target_confirmation_receipt,
        existing_selection_reused=existing_selection_reused,
    )
    if blocker is not None:
        block_execution(execution, blocker)
        return execution
    source_count = len([item for item in selection.get("source_databases", []) if isinstance(item, Mapping)])
    start_step(
        execution,
        "classifying_merge_route",
        f"Inspecting {source_count} selected source database(s) and classifying the additive merge route.",
    )
    preflight = runtime.merge_adapter.multi_source_merge_preflight({"selection": selection})
    blocker = blocker_from_adapter_result("classifying_merge_route", preflight, function_name="database_merge_additive_only")
    if blocker is not None:
        block_execution(execution, blocker)
        return execution
    execution.artifacts["preflight"] = _adapter_output(preflight)
    execution.artifacts["locks"] = [
        {
            "lock_id": f"lock_{execution.merge_run_id}",
            "lock_type": "merge",
            "merge_run_id": execution.merge_run_id,
            "status": "active",
            "target_artifact_root": selection["target_artifact_root"],
            "target_database_path": selection["target_database_path"],
        }
    ]
    if selection["merge_route"] == "empty_databases_merge_path":
        return empty_databases_merge_path(
            runtime=runtime,
            selection=selection,
            execution=execution,
            reconciliation_receipt=reconciliation_receipt,
        )
    return filled_databases_merge_path(
        runtime=runtime,
        selection=selection,
        execution=execution,
        reconciliation_receipt=reconciliation_receipt,
    )


def _adapter_output(result: object) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        payload = result.to_dict()
        output = payload.get("output_refs")
        return dict(output) if isinstance(output, Mapping) else {}
    return dict(result) if isinstance(result, Mapping) else {}
