from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunExecution, PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime, pipeline_run


def manual_pipeline_run(
    *,
    runtime: PipelineRunRuntime,
    target: PipelineRunTarget | None,
    input_files: Sequence[Mapping[str, Any] | PipelineInputFile],
    workflow_run_id: str | None = None,
    confirmation: Mapping[str, Any] | None = None,
) -> PipelineRunExecution:
    return pipeline_run(
        runtime=runtime,
        target=target,
        input_files=input_files,
        workflow_run_id=workflow_run_id,
        batch_kind="manual_ingest",
        confirmation=confirmation,
        workflow_tool="manual_pipeline_run",
    )
