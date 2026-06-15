from __future__ import annotations

import inspect
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.adapter_results import AdapterCallResult
from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunExecution, PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.progress_bridge import (
    OrchestratorSnapshotProgressBridge,
    pipeline_snapshot_path,
)
from semantic_control_kernel.workflows.pipeline_run.run_support import (
    _adapter_ref,
    _block,
    _blocker_from_adapter_result,
    _complete,
    _orchestrator_ui_state,
)


def launch_or_restore_owner_run(
    *,
    runtime,
    target: PipelineRunTarget,
    execution: PipelineRunExecution,
    normalized_inputs: Sequence[PipelineInputFile],
    workflow_run_id: str,
    pipeline_batch_id: str,
    resume_state: Mapping[str, Any] | None,
) -> AdapterCallResult | object | None:
    if resume_state and resume_state.get("owner_run_completed"):
        return AdapterCallResult(dict(resume_state.get("owner_adapter_result", {})))
    state_paths = StatePaths.from_state_root(runtime.state_root)
    snapshot_path = pipeline_snapshot_path(
        state_paths,
        workflow_run_id,
        pipeline_batch_id,
        artifact_root=target.artifact_root_path,
    )
    progress_bridge = OrchestratorSnapshotProgressBridge(
        state_paths,
        workflow_run_id=workflow_run_id,
        workflow_tool=execution.workflow_tool,
        snapshot_path=snapshot_path,
    )
    owner_result = _call_orchestrator_run(
        runtime.orchestrator_adapter,
        _owner_payload(target, normalized_inputs, workflow_run_id, pipeline_batch_id, snapshot_path),
        progress_callback=progress_bridge.poll,
    )
    progress_bridge.poll()
    blocker = _blocker_from_adapter_result("running_pipeline", owner_result, before_owner_mutation=False)
    if blocker is not None:
        _block(execution, blocker)
        return None
    _complete(execution, "running_pipeline", "OrchestratorAdapter.run_pipeline", pipeline_adapter_receipts=[_adapter_ref(owner_result)])
    return owner_result


def _owner_payload(
    target: PipelineRunTarget,
    normalized_inputs: Sequence[PipelineInputFile],
    workflow_run_id: str,
    pipeline_batch_id: str,
    snapshot_path,
) -> dict[str, Any]:
    return {
        "workflow_run_id": workflow_run_id,
        "target_identity": target.target_identity,
        "pipeline_batch_id": pipeline_batch_id,
        "snapshot_path": str(snapshot_path),
        "ui_state": _orchestrator_ui_state(target),
        "input_files": [item.to_manifest_entry() for item in normalized_inputs],
        "active_database": target.active_database_manifest_ref(),
        "semantic_release": target.semantic_release_manifest_ref(),
        "active_projections": target.projection_manifest_refs(),
    }


def _call_orchestrator_run(orchestrator_adapter: Any, owner_payload: Mapping[str, Any], *, progress_callback) -> object:
    method = orchestrator_adapter.run_pipeline
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        signature = None
    if signature is not None and "progress_callback" in signature.parameters:
        return method(owner_payload, progress_callback=progress_callback)
    return method(owner_payload)
