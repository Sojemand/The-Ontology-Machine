from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.debug.llm_diagnostics import LLMAttemptDiagnosticRecorder
from semantic_control_kernel.repository.paths import StatePaths


class LLMAttemptDiagnosticSink:
    def __init__(self, recorder: LLMAttemptDiagnosticRecorder | None) -> None:
        self.recorder = recorder

    @classmethod
    def from_state_paths(cls, state_paths: StatePaths | None) -> "LLMAttemptDiagnosticSink":
        if state_paths is None:
            return cls(None)
        return cls(LLMAttemptDiagnosticRecorder(state_paths))

    def record_failed_attempt(
        self,
        *,
        workflow_run_id: str,
        workflow_tool: str,
        analysis_run_id: str,
        llm_function_name: str,
        attempt_index: int,
        max_attempts: int,
        attempted_schema: str,
        parse_status: str,
        validation_status: str,
        validation_error_summary: str,
        artifact_refs: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        if self.recorder is None:
            return None
        payload = self.recorder.record_failed_attempt(
            workflow_run_id=workflow_run_id,
            workflow_tool=workflow_tool,
            analysis_run_id=analysis_run_id,
            llm_function_name=llm_function_name,
            attempt_index=attempt_index,
            max_attempts=max_attempts,
            attempted_schema=attempted_schema,
            parse_status=parse_status,
            validation_status=validation_status,
            validation_error_summary=validation_error_summary,
            artifact_refs=artifact_refs,
        )
        return {
            "llm_attempt_id": payload["llm_attempt_id"],
            "diagnostic_ref": f"debug/llm_attempts/{analysis_run_id}/{attempt_index:06d}_{payload['llm_attempt_id']}.json",
        }
