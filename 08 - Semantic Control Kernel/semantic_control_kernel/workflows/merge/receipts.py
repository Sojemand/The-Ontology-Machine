from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.atomic_json import atomic_write_json
from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import StatePaths, path_hash, stable_hash, utc_iso
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
from semantic_control_kernel.types.events import ProgressEvent
from semantic_control_kernel.types.merge import MergeWorkflowBlocker, MergeWorkflowExecution
from semantic_control_kernel.types.receipts import OperationReceipt


STEP_LABELS = {
    "classifying_merge_route": "Classifying merge route",
    "creating_target_artifact_tree": "Creating target Artifact Tree",
    "creating_target_database": "Creating target database",
    "running_empty_merge": "Merging empty source databases",
    "running_filled_merge": "Copying source databases and artifacts",
    "building_collision_manifest": "Building Semantic Release collision manifest",
    "awaiting_reconciliation": "Reconciling merge collisions",
    "backfill_sql": "Backfilling merge metadata",
    "attaching_semantic_release": "Attaching merged Semantic Release",
    "activating_semantic_release": "Activating merged Semantic Release",
    "completed": "Database merge completed",
}


def start_step(execution: MergeWorkflowExecution, step_id: str, summary: str) -> None:
    append_progress(execution, step_id, status=ProgressStatus.STEP_STARTED.value, summary=summary)


def append_progress(execution: MergeWorkflowExecution, step_id: str, *, status: str, summary: str) -> None:
    paths = StatePaths.from_state_root(execution.state_root)
    paths.ensure_layout()
    progress_store = ProgressEventStore(paths)
    event = progress_store.append_progress_event_with_next_sequence(
        {
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "workflow_run_id": execution.workflow_run_id,
            "workflow_tool": execution.workflow_tool,
            "step_id": step_id,
            "step_label": STEP_LABELS.get(step_id, step_id),
            "event_type": ProgressEventType.WORKFLOW_STEP.value,
            "status": status,
            "user_visible_summary": summary,
            "current_state_summary": execution.final_state,
            "timestamp": utc_iso(),
        }
    )
    execution.progress_events.append(event.to_dict())


def complete_step(
    execution: MergeWorkflowExecution,
    *,
    step_id: str,
    function_name: str,
    output_refs: Sequence[Mapping[str, Any]] = (),
    adapter_results: Sequence[object] = (),
    final_state: str | None = None,
) -> dict[str, Any]:
    if final_state is not None:
        execution.final_state = final_state
    receipt = OperationReceipt.from_dict(
        {
        "schema_version": "kernel.operation_receipt.v1",
        "operation_receipt_id": generate_id("operation_receipt_id"),
        "function_name": function_name,
        "workflow_run_id": execution.workflow_run_id,
        "target_identity_before": _target_identity(execution),
        "target_identity_after": _target_identity(execution),
        "input_artifact_refs": [],
        "output_artifact_refs": [dict(item) for item in output_refs],
        "final_kernel_state": {"state": execution.final_state},
        "created_at": utc_iso(),
        "pipeline_adapter_receipts": [_adapter_receipt(item) for item in adapter_results],
        }
    )
    execution.operation_receipts.append(receipt.to_dict())
    execution.completed_step_ids.append(step_id)
    execution.operation_log.append(function_name)
    progress_status = ProgressStatus.COMPLETED.value if step_id == "completed" else ProgressStatus.STEP_COMPLETED.value
    append_progress(execution, step_id, status=progress_status, summary=_completion_summary(step_id))
    execution.resume_state = resume_state_for(execution, last_completed_step=step_id)
    return receipt


def block_execution(execution: MergeWorkflowExecution, blocker: MergeWorkflowBlocker, *, final_state: str = "blocked") -> None:
    execution.status = "blocked"
    execution.final_state = final_state
    execution.blocker = blocker
    execution.blocked_step_id = blocker.step_id
    append_progress(execution, blocker.step_id, status="blocked", summary=blocker.user_visible_summary)
    execution.resume_state = resume_state_for(execution, last_completed_step=execution.completed_step_ids[-1] if execution.completed_step_ids else "")
    from semantic_control_kernel.workflows.merge.final_notice import append_merge_final_notice

    append_merge_final_notice(execution)


def _completion_summary(step_id: str) -> str:
    if step_id == "completed":
        return "Database merge workflow completed."
    return f"{STEP_LABELS.get(step_id, step_id)} completed."


def blocker_from_missing_capability(step_id: str, blocker: MissingCapabilityBlocker) -> MergeWorkflowBlocker:
    payload = blocker.to_dict()
    return MergeWorkflowBlocker(
        blocker_code="pipeline_capability_missing",
        step_id=step_id,
        function_or_route=str(payload.get("kernel_function", "")),
        recovery_state_class=str(payload.get("recovery_state_class", "support_only_unrecoverable")),
        user_visible_summary=str(payload.get("blocking_reason", "Required Pipeline capability is missing.")),
        diagnostics=tuple(dict(item) for item in payload.get("diagnostics", []) if isinstance(item, Mapping)),
    )


def blocker_from_adapter_result(step_id: str, result: object, *, function_name: str) -> MergeWorkflowBlocker | None:
    if isinstance(result, MissingCapabilityBlocker):
        return blocker_from_missing_capability(step_id, result)
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return MergeWorkflowBlocker(
            blocker_code=result.status,
            step_id=step_id,
            function_or_route=function_name,
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary=f"Pipeline adapter returned {result.status}.",
            diagnostics=tuple(dict(item) for item in result.to_dict().get("diagnostics", []) if isinstance(item, Mapping)),
        )
    if result is None:
        return MergeWorkflowBlocker(
            blocker_code="invalid_owner_response",
            step_id=step_id,
            function_or_route=function_name,
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Pipeline adapter returned no result.",
        )
    return None


def adapter_output(result: object) -> dict[str, Any]:
    if isinstance(result, AdapterCallResult):
        output = result.to_dict().get("output_refs")
        return dict(output) if isinstance(output, Mapping) else {}
    if isinstance(result, Mapping):
        return dict(result)
    return {}


def write_json(path: str | Path, payload: Mapping[str, Any]) -> str:
    target = Path(path)
    atomic_write_json(target, dict(payload))
    return str(target)


def merge_run_dir(target_artifact_root: str | Path, merge_run_id: str) -> Path:
    return Path(target_artifact_root) / "Documents" / "logs" / "merge_runs" / require_state_id("merge_run_id", merge_run_id)


def resume_state_for(execution: MergeWorkflowExecution, *, last_completed_step: str) -> dict[str, Any]:
    selection = execution.selection or {}
    return {
        "adapter_call_refs": _resume_adapter_receipts(execution),
        "collision_manifest_fingerprint": str((execution.artifacts.get("collision_manifest") or {}).get("manifest_fingerprint", "")) if isinstance(execution.artifacts.get("collision_manifest"), Mapping) else "",
        "id_map_fingerprint": str((execution.artifacts.get("id_map") or {}).get("map_fingerprint", "")) if isinstance(execution.artifacts.get("id_map"), Mapping) else "",
        "last_completed_step": last_completed_step,
        "merge_run_id": execution.merge_run_id,
        "pending_interaction_id": str(execution.artifacts.get("pending_interaction_id", "")),
        "source_selection_fingerprint": str(selection.get("selection_fingerprint", "")),
        "target_identity": _target_identity(execution),
    }


def _target_identity(execution: MergeWorkflowExecution) -> dict[str, Any]:
    selection = execution.selection or {}
    target_artifact_root = str(selection.get("target_artifact_root", ""))
    target_database_path = str(selection.get("target_database_path", ""))
    source_database_ids = sorted(
        str(item.get("source_database_id", ""))
        for item in selection.get("source_databases", [])
        if isinstance(item, Mapping)
    )
    artifact_root_path_hash = path_hash(target_artifact_root) if target_artifact_root else ""
    database_path_hash = path_hash(target_database_path) if target_database_path else ""
    source_database_set_hash = stable_hash("|".join(source_database_ids)) if source_database_ids else ""
    return {
        "schema_version": "state.target_identity.v1",
        "artifact_root_path_hash": artifact_root_path_hash,
        "database_path_hash": database_path_hash,
        "source_database_set_hash": source_database_set_hash,
        "workflow_run_id": execution.workflow_run_id,
        "lock_scope": "merge",
        "target_hash": stable_hash(
            f"{artifact_root_path_hash}:{database_path_hash}:{source_database_set_hash}:{execution.workflow_run_id}"
        ),
        "created_from": "merge.workflow",
    }


def _adapter_receipt(result: object) -> dict[str, Any]:
    if isinstance(result, AdapterCallResult):
        payload = result.to_dict()
        return {
            "adapter_call_id": payload.get("adapter_call_id", ""),
            "adapter_name": payload.get("adapter_name", ""),
            "status": payload.get("status", ""),
        }
    if isinstance(result, MissingCapabilityBlocker):
        return result.to_dict()
    if isinstance(result, Mapping):
        return dict(result)
    return {}


def _resume_adapter_receipts(execution: MergeWorkflowExecution) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for operation_receipt in execution.operation_receipts:
        if not isinstance(operation_receipt, Mapping):
            continue
        for adapter_receipt in operation_receipt.get("pipeline_adapter_receipts", []):
            if isinstance(adapter_receipt, Mapping):
                receipts.append(dict(adapter_receipt))
    return receipts
