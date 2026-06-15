from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from semantic_control_kernel.types.llm_call_common import JsonObject, _copy_mapping, _copy_sequence


@dataclass(frozen=True)
class LLMAttemptMetadata:
    analysis_run_id: str
    llm_function_name: str
    attempt_index: int
    max_attempts: int
    started_at: str
    ended_at: str
    failure_kind: str | None
    next_action: str

    SCHEMA_VERSION = "kernel.llm_attempt_metadata.v1"

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "analysis_run_id": self.analysis_run_id,
            "llm_function_name": self.llm_function_name,
            "attempt_index": self.attempt_index,
            "max_attempts": self.max_attempts,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "failure_kind": self.failure_kind,
            "next_action": self.next_action,
        }


@dataclass(frozen=True)
class LLMValidationReport:
    llm_function_name: str
    attempt_index: int
    attempted_schema: str
    parse_status: str
    validation_status: str
    error_codes: tuple[str, ...] = ()
    error_summary: str = ""
    blocking_paths: tuple[str, ...] = ()

    SCHEMA_VERSION = "kernel.llm_validation_report.v1"

    @property
    def passed(self) -> bool:
        return self.validation_status == "passed"

    def compact_feedback(self) -> str:
        if self.passed:
            return ""
        codes = ", ".join(self.error_codes) if self.error_codes else "validation_failed"
        paths = ", ".join(self.blocking_paths[:5])
        if paths:
            return f"{codes}: {self.error_summary} Blocking paths: {paths}."
        return f"{codes}: {self.error_summary}"

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "llm_function_name": self.llm_function_name,
            "attempt_index": self.attempt_index,
            "attempted_schema": self.attempted_schema,
            "parse_status": self.parse_status,
            "validation_status": self.validation_status,
            "error_codes": list(self.error_codes),
            "error_summary": self.error_summary,
            "blocking_paths": list(self.blocking_paths),
        }


@dataclass(frozen=True)
class LLMFinalError:
    error_code: str
    category: str
    llm_function_name: str
    workflow_run_id: str
    analysis_run_id: str
    attempted_schema: str
    attempts_used: int
    failed_attempt_artifact_refs: tuple[Mapping[str, Any], ...]
    support_bundle_ref: Mapping[str, Any]
    validation_error_summary: str = ""
    preserved_state_summary: Mapping[str, Any] = field(default_factory=dict)
    recovery_options: tuple[Mapping[str, Any], ...] = ()
    allowed_agent_tools: tuple[str, ...] = ()

    SCHEMA_VERSION = "kernel.llm_final_error.v1"

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "error_code": self.error_code,
            "category": self.category,
            "llm_function_name": self.llm_function_name,
            "workflow_run_id": self.workflow_run_id,
            "analysis_run_id": self.analysis_run_id,
            "attempted_schema": self.attempted_schema,
            "attempts_used": self.attempts_used,
            "failed_attempt_artifact_refs": _copy_sequence(self.failed_attempt_artifact_refs),
            "support_bundle_ref": _copy_mapping(self.support_bundle_ref),
            "validation_error_summary": self.validation_error_summary,
            "preserved_state_summary": _copy_mapping(self.preserved_state_summary),
            "recovery_options": _copy_sequence(self.recovery_options),
            "allowed_agent_tools": list(self.allowed_agent_tools),
        }


@dataclass(frozen=True)
class LLMCallResult:
    status: str
    llm_function_name: str
    workflow_run_id: str
    analysis_run_id: str
    output_artifact_ref: Mapping[str, Any] | None = None
    output: Any = None
    final_error: LLMFinalError | None = None
    mirror_event: Mapping[str, Any] | None = None
    attempts_used: int = 0
    retry_events: tuple[Mapping[str, Any], ...] = ()
    provider_call_count: int = 0

    @property
    def succeeded(self) -> bool:
        return self.status == "succeeded"

    def to_dict(self) -> JsonObject:
        payload: JsonObject = {
            "status": self.status,
            "llm_function_name": self.llm_function_name,
            "workflow_run_id": self.workflow_run_id,
            "analysis_run_id": self.analysis_run_id,
            "attempts_used": self.attempts_used,
            "provider_call_count": self.provider_call_count,
            "retry_events": _copy_sequence(self.retry_events),
        }
        if self.output_artifact_ref is not None:
            payload["output_artifact_ref"] = _copy_mapping(self.output_artifact_ref)
        if self.output is not None:
            payload["output"] = deepcopy(self.output)
        if self.final_error is not None:
            payload["final_error"] = self.final_error.to_dict()
        if self.mirror_event is not None:
            payload["mirror_event"] = _copy_mapping(self.mirror_event)
        return payload


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True
