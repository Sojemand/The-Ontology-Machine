from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
from semantic_control_kernel.types.events import ProgressEvent
from semantic_control_kernel.types.receipts import OperationReceipt
from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker, RebuildWorkflowExecution


def complete_step(
    execution: RebuildWorkflowExecution,
    step_id: str,
    function_name: str,
    *,
    adapter_results: list[object | None] | None = None,
    final_state: str | None = None,
    summary: str | None = None,
) -> str:
    if final_state is not None:
        execution.final_state = final_state
    receipt = OperationReceipt.from_dict(
        {
            "schema_version": "kernel.operation_receipt.v1",
            "operation_receipt_id": generate_id("operation_receipt_id"),
            "function_name": function_name,
            "workflow_run_id": execution.workflow_run_id,
            "target_identity_before": execution.target_identity,
            "target_identity_after": execution.target_identity,
            "input_artifact_refs": [],
            "output_artifact_refs": [],
            "final_kernel_state": {"state": execution.final_state},
            "created_at": utc_iso(),
            "pipeline_adapter_receipts": [{"adapter_call_id": adapter_call_id(item)} for item in adapter_results or [] if item is not None],
        }
    )
    receipt_id = receipt.payload["operation_receipt_id"]
    execution.operation_receipts.append(receipt.to_dict())
    execution.completed_step_ids.append(step_id)
    execution.operation_log.append(function_name)
    progress_status = ProgressStatus.COMPLETED.value if step_id == "completed" else ProgressStatus.STEP_COMPLETED.value
    append_progress(
        execution,
        step_id,
        status=progress_status,
        summary=summary or f"{step_id} completed.",
        receipt_refs=[{"operation_receipt_id": receipt_id}],
    )
    execution.resume_state = {
        "adapter_call_refs": [{"adapter_call_id": adapter_call_id(item)} for item in adapter_results or [] if item is not None],
        "last_completed_step": step_id,
        "overwrite_receipt_id": execution.artifacts.get("overwrite_receipt_id", ""),
        "rebuild_run_id": execution.rebuild_run_id,
        "target_identity": execution.target_identity,
    }
    return receipt_id


def start_step(execution: RebuildWorkflowExecution, step_id: str, summary: str) -> None:
    append_progress(execution, step_id, status=ProgressStatus.STEP_STARTED.value, summary=summary)


def block_execution(execution: RebuildWorkflowExecution, blocker: RebuildWorkflowBlocker) -> None:
    execution.status = "blocked"
    execution.final_state = blocker.recovery_state_class
    execution.blocked_step_id = blocker.step_id
    execution.blocker = blocker
    append_progress(execution, blocker.step_id, status="blocked", summary=blocker.user_visible_summary)
    for lock in execution.artifacts.get("locks", []):
        if lock.get("status") == "active":
            lock["status"] = "failed"
    from semantic_control_kernel.workflows.rebuild.final_notice import append_rebuild_final_notice

    append_rebuild_final_notice(execution)


def append_progress(
    execution: RebuildWorkflowExecution,
    step_id: str,
    *,
    status: str,
    summary: str,
    receipt_refs: list[Mapping[str, Any]] | None = None,
) -> None:
    paths = StatePaths.from_state_root(execution.state_root)
    paths.ensure_layout()
    progress_store = ProgressEventStore(paths)
    event = ProgressEvent.from_dict(
        {
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "workflow_run_id": execution.workflow_run_id,
            "workflow_tool": execution.workflow_tool,
            "step_id": step_id,
            "step_label": step_id,
            "event_type": ProgressEventType.WORKFLOW_STEP.value,
            "status": status,
            "sequence_index": len(progress_store.list_progress_events(execution.workflow_run_id)) + 1,
            "user_visible_summary": summary,
            "current_state_summary": execution.final_state,
            "timestamp": utc_iso(),
            "receipt_refs": [dict(item) for item in receipt_refs or ()],
        }
    )
    progress_store.append_progress_event(event)
    execution.progress_events.append(event.to_dict())


def embedding_completion_summary(embedding_result: str, adapter_result: object | None) -> str:
    output = adapter_output_refs(adapter_result)
    count = output.get("embedding_count")
    reason = str(output.get("embedding_reason") or "").strip()
    result = str(embedding_result or "").strip()
    if result == "created":
        return f"Embedding vectors created for {count} records." if count not in (None, "") else "Embedding vectors created."
    if result == "skipped_unconfigured":
        return f"Embedding generation skipped: {reason}" if reason else "Embedding generation skipped because the provider is not configured."
    return f"Embedding step finished with result: {result}."


def adapter_output_refs(value: object | None) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
        output = payload.get("output_refs") if isinstance(payload, Mapping) else {}
        return dict(output) if isinstance(output, Mapping) else {}
    if isinstance(value, Mapping):
        output = value.get("output_refs")
        return dict(output) if isinstance(output, Mapping) else {}
    return {}


def blocker_from_result(step_id: str, result: object, function_name: str) -> RebuildWorkflowBlocker | None:
    from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker

    if isinstance(result, MissingCapabilityBlocker):
        payload = result.to_dict()
        return RebuildWorkflowBlocker(
            blocker_code="pipeline_capability_missing",
            step_id=step_id,
            function_or_route=str(payload.get("kernel_function", function_name)),
            recovery_state_class=str(payload.get("recovery_state_class", "support_only_unrecoverable")),
            user_visible_summary=str(payload.get("blocking_reason", "Required Pipeline capability is missing.")),
            diagnostics=tuple(dict(item) for item in payload.get("diagnostics", []) if isinstance(item, Mapping)),
        )
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return RebuildWorkflowBlocker(
            blocker_code=result.status,
            step_id=step_id,
            function_or_route=function_name,
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary=f"Pipeline adapter returned {result.status}.",
            diagnostics=tuple(dict(item) for item in result.to_dict().get("diagnostics", []) if isinstance(item, Mapping)),
        )
    return None


def adapter_call_id(value: object | None) -> str:
    if value is None:
        return ""
    if hasattr(value, "to_dict"):
        return str(value.to_dict().get("adapter_call_id", ""))
    if isinstance(value, Mapping):
        return str(value.get("adapter_call_id", ""))
    return ""


def invalid_owner_response(step_id: str) -> RebuildWorkflowBlocker:
    return RebuildWorkflowBlocker("invalid_owner_response", step_id, step_id, "support_only_unrecoverable", "Rebuild owner returned an invalid response.")


def release_locks(execution: RebuildWorkflowExecution) -> None:
    for lock in execution.artifacts.get("locks", []):
        if lock.get("status") == "active":
            lock["status"] = "released"
