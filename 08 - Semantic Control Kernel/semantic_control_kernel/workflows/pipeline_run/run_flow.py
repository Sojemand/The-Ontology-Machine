from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.policy.batch_policy import allocate_pipeline_batch_id, artifact_ref
from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunExecution, PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.batch_manifest import (
    build_pending_batch_manifest,
    write_pending_manifest,
)
from semantic_control_kernel.workflows.pipeline_run.run_finalize import finalize_pipeline_run
from semantic_control_kernel.workflows.pipeline_run.run_owner import launch_or_restore_owner_run
from semantic_control_kernel.workflows.pipeline_run.run_runtime import PipelineRunRuntime
from semantic_control_kernel.workflows.pipeline_run.run_support import (
    _adapter_ref,
    _block,
    _blocker_from_adapter_result,
    _complete,
    _normalize_inputs,
    _precondition_blocker,
    _resume_preflight_blocker,
    create_blocker,
)


def pipeline_run(
    *,
    runtime: PipelineRunRuntime,
    target: PipelineRunTarget | None,
    input_files: Sequence[Mapping[str, Any] | PipelineInputFile] = (),
    workflow_run_id: str | None = None,
    batch_kind: str = "manual_ingest",
    confirmation: Mapping[str, Any] | None = None,
    attempt_index: int = 1,
    resume_state: Mapping[str, Any] | None = None,
    workflow_tool: str = "pipeline_run",
) -> PipelineRunExecution:
    resolved_workflow_run_id = workflow_run_id or (target.workflow_run_id if target else "wr_missing_target")
    execution = PipelineRunExecution(
        workflow_run_id=resolved_workflow_run_id,
        workflow_tool=workflow_tool,
        state_root=Path(runtime.state_root),
        target=target,
    )
    normalized_inputs = _normalize_inputs(input_files)
    if _block_preconditions(execution, target, normalized_inputs, confirmation, resume_state, workflow_tool):
        return execution
    assert target is not None

    pipeline_batch_id = _pipeline_batch_id(resolved_workflow_run_id, attempt_index, resume_state)
    pending = _prepare_and_register_batch(
        runtime=runtime,
        target=target,
        execution=execution,
        workflow_run_id=resolved_workflow_run_id,
        pipeline_batch_id=pipeline_batch_id,
        batch_kind=batch_kind,
        normalized_inputs=normalized_inputs,
    )
    if pending is None:
        return execution
    owner_result = launch_or_restore_owner_run(
        runtime=runtime,
        target=target,
        execution=execution,
        normalized_inputs=normalized_inputs,
        workflow_run_id=resolved_workflow_run_id,
        pipeline_batch_id=pipeline_batch_id,
        resume_state=resume_state,
    )
    if owner_result is None:
        return execution
    return finalize_pipeline_run(
        runtime=runtime,
        target=target,
        execution=execution,
        pending=pending,
        owner_result=owner_result,
        workflow_run_id=resolved_workflow_run_id,
        pipeline_batch_id=pipeline_batch_id,
    )


def _block_preconditions(execution: PipelineRunExecution, target: PipelineRunTarget | None, normalized_inputs: Sequence[PipelineInputFile], confirmation: Mapping[str, Any] | None, resume_state: Mapping[str, Any] | None, workflow_tool: str) -> bool:
    blocker = _precondition_blocker(target, normalized_inputs, confirmation, workflow_tool=workflow_tool)
    if blocker is not None:
        _block(execution, blocker)
        return True
    if resume_state and resume_state.get("owner_run_completed") and not resume_state.get("correlation_pending"):
        _block(
            execution,
            create_blocker(
                step_id="resume_preflight",
                function_or_route="pipeline_run",
                blocker_code="duplicate_owner_run_prevented",
                recovery_state_class="partial_pipeline_run",
                summary="Resume state does not allow launching a second owner run for the same batch.",
            ),
        )
        return True
    resume_blocker = _resume_preflight_blocker(target, resume_state)
    if resume_blocker is not None:
        _block(execution, resume_blocker)
        return True
    return False


def _pipeline_batch_id(workflow_run_id: str, attempt_index: int, resume_state: Mapping[str, Any] | None) -> str:
    if isinstance(resume_state, Mapping) and resume_state.get("pipeline_batch_id"):
        return str(resume_state.get("pipeline_batch_id"))
    return str(allocate_pipeline_batch_id(workflow_run_id, attempt_index=attempt_index))


def _prepare_and_register_batch(
    *,
    runtime,
    target: PipelineRunTarget,
    execution: PipelineRunExecution,
    workflow_run_id: str,
    pipeline_batch_id: str,
    batch_kind: str,
    normalized_inputs: Sequence[PipelineInputFile],
) -> Mapping[str, Any] | None:
    pending = build_pending_batch_manifest(
        target=target,
        workflow_run_id=workflow_run_id,
        pipeline_batch_id=pipeline_batch_id,
        batch_kind=batch_kind,
        input_files=normalized_inputs,
        created_by_workflow=execution.workflow_tool,
    )
    pending_path = write_pending_manifest(target, pending)
    execution.artifacts["pending_manifest"] = pending
    execution.artifacts["pending_manifest_path"] = str(pending_path)
    _complete(execution, "preparing_batch", "create_pending_pipeline_batch_manifest", output_refs=[artifact_ref(pending_path, target.artifact_root)])
    create_result = runtime.batch_adapter.create_batch_manifest(
        {
            "workflow_run_id": workflow_run_id,
            "target_identity": target.target_identity,
            "pipeline_batch_id": pipeline_batch_id,
            "batch_kind": batch_kind,
            "active_database": target.active_database_manifest_ref(),
            "artifact_root": target.artifact_root_path,
            "semantic_release": target.semantic_release_manifest_ref(),
            "active_projections": target.projection_manifest_refs(),
            "input_files": [item.to_manifest_entry() for item in normalized_inputs],
            "pending_manifest": pending,
        }
    )
    blocker = _blocker_from_adapter_result("create_batch_manifest", create_result, before_owner_mutation=True)
    if blocker is not None:
        _block(execution, blocker)
        return None
    _complete(execution, "create_batch_manifest", "BatchReingestAdapter.create_batch_manifest", pipeline_adapter_receipts=[_adapter_ref(create_result)])
    return pending
