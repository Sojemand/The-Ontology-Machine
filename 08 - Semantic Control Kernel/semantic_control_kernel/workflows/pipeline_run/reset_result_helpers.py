from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.adapter_results import AdapterCallResult
from semantic_control_kernel.types.batches import PipelineRunExecution
from semantic_control_kernel.workflows.pipeline_run.run import create_blocker


def adapter_output(result: object) -> dict[str, Any]:
    if isinstance(result, AdapterCallResult):
        value = result.to_dict().get("output_refs")
        return dict(value) if isinstance(value, Mapping) else {}
    return dict(result) if isinstance(result, Mapping) else {}


def adapter_ref(result: object) -> dict[str, Any]:
    if isinstance(result, AdapterCallResult):
        payload = result.to_dict()
        return {
            "adapter_call_id": payload.get("adapter_call_id", ""),
            "adapter_name": payload.get("adapter_name", ""),
            "status": payload.get("status", ""),
        }
    return dict(result) if isinstance(result, Mapping) else {}


def manifest_ref(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {key: manifest[key] for key in ("pipeline_batch_id", "manifest_fingerprint") if key in manifest}


def block(execution: PipelineRunExecution, code: str, recovery: str, summary: str) -> None:
    blocker = create_blocker(
        step_id="resetting_database",
        function_or_route="reset_database",
        blocker_code=code,
        recovery_state_class=recovery,
        summary=summary,
    )
    execution.status = "blocked"
    execution.blocker = blocker
    execution.blocked_step_id = blocker.step_id
    progress(execution, blocker.step_id, "blocked", blocker_code=code)


def progress(execution: PipelineRunExecution, step_id: str, status: str, **extra: Any) -> None:
    event = {
        "workflow_run_id": execution.workflow_run_id,
        "workflow_tool": execution.workflow_tool,
        "step_id": step_id,
        "status": status,
    }
    event.update(extra)
    execution.progress_events.append(event)
