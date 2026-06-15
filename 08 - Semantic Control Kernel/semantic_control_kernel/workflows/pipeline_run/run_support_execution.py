from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunExecution, PipelineRunTarget, PipelineRunBlocker


def _orchestrator_ui_state(target: PipelineRunTarget) -> dict[str, Any]:
    return {
        "input_folder": target.input_path,
        "artifact_folder": target.artifact_root_path,
        "semantic_release_path": "",
        "corpus_output_folder": target.corpus_path,
        "selected_corpus_db_path": target.database_path,
        "semantic_release_mode": "database_default",
        "mode": "batch",
    }


def _normalize_inputs(input_files: Sequence[Mapping[str, Any] | PipelineInputFile]) -> list[PipelineInputFile]:
    normalized = []
    for item in input_files:
        normalized.append(item if isinstance(item, PipelineInputFile) else PipelineInputFile.from_mapping(item))
    return normalized


def _owner_final_manifest(owner_output: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = owner_output.get("final_manifest")
    return value if isinstance(value, Mapping) else None


def _complete(
    execution: PipelineRunExecution,
    step_id: str,
    function_name: str,
    *,
    output_refs: Sequence[Mapping[str, Any]] = (),
    pipeline_adapter_receipts: Sequence[Mapping[str, Any]] = (),
) -> None:
    execution.completed_step_ids.append(step_id)
    execution.operation_log.append(function_name)
    receipt = {
        "function_name": function_name,
        "workflow_run_id": execution.workflow_run_id,
        "target_identity": execution.target_identity,
        "output_artifact_refs": [dict(item) for item in output_refs],
        "pipeline_adapter_receipts": [dict(item) for item in pipeline_adapter_receipts],
    }
    execution.operation_receipts.append(receipt)
    execution.progress_events.append(
        {
            "workflow_run_id": execution.workflow_run_id,
            "workflow_tool": execution.workflow_tool,
            "step_id": step_id,
            "status": "step_completed",
        }
    )


def _block(execution: PipelineRunExecution, blocker: PipelineRunBlocker) -> None:
    execution.status = "blocked"
    execution.blocked_step_id = blocker.step_id
    execution.blocker = blocker
    execution.progress_events.append(
        {
            "workflow_run_id": execution.workflow_run_id,
            "workflow_tool": execution.workflow_tool,
            "step_id": blocker.step_id,
            "status": "blocked",
            "blocker_code": blocker.blocker_code,
        }
    )
