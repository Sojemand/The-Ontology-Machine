"""UI mixin for the hidden pipeline-log reset action."""

from __future__ import annotations

from . import workflow


class PipelineLogResetAppActions:
    def _reset_pipeline_logs(self) -> None:
        workflow.reset_pipeline_logs(self)
