from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.batch_common import JsonObject, SEMANTIC_RELEASE_ACTIVE, _copy_mapping, _copy_sequence
from semantic_control_kernel.types.batch_target import PipelineRunTarget


@dataclass(frozen=True)
class PipelineRunBlocker:
    blocker_code: str
    step_id: str
    function_or_route: str
    recovery_state_class: str
    user_visible_summary: str
    diagnostics: tuple[Mapping[str, Any], ...] = ()
    support_bundle_ref: Mapping[str, Any] | None = None
    resume_descriptor: Mapping[str, Any] | None = None

    def to_dict(self) -> JsonObject:
        payload: JsonObject = {
            "blocker_code": self.blocker_code,
            "step_id": self.step_id,
            "function_or_route": self.function_or_route,
            "recovery_state_class": self.recovery_state_class,
            "user_visible_summary": self.user_visible_summary,
            "diagnostics": _copy_sequence(self.diagnostics),
        }
        if self.support_bundle_ref is not None:
            payload["support_bundle_ref"] = _copy_mapping(self.support_bundle_ref)
        if self.resume_descriptor is not None:
            payload["resume_descriptor"] = _copy_mapping(self.resume_descriptor)
        return payload


@dataclass
class PipelineRunExecution:
    workflow_run_id: str
    workflow_tool: str
    state_root: Path
    target: PipelineRunTarget | None = None
    status: str = "running"
    final_state: str = SEMANTIC_RELEASE_ACTIVE
    completed_step_ids: list[str] = field(default_factory=list)
    blocked_step_id: str | None = None
    blocker: PipelineRunBlocker | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    operation_log: list[str] = field(default_factory=list)
    progress_events: list[dict[str, Any]] = field(default_factory=list)
    operation_receipts: list[dict[str, Any]] = field(default_factory=list)
    mirror_events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def target_identity(self) -> JsonObject:
        return self.target.target_identity if self.target is not None else {}

    @property
    def state_snapshot_id(self) -> str:
        if self.target is None:
            return stable_hash(f"{self.workflow_run_id}:{self.workflow_tool}:no-target")
        return stable_hash(
            f"{self.workflow_run_id}:{self.workflow_tool}:{self.target.state_snapshot_id}:{','.join(self.completed_step_ids)}"
        )

    def to_dict(self) -> JsonObject:
        return {
            "workflow_run_id": self.workflow_run_id,
            "workflow_tool": self.workflow_tool,
            "status": self.status,
            "final_state": self.final_state,
            "completed_step_ids": list(self.completed_step_ids),
            "blocked_step_id": self.blocked_step_id,
            "blocker": self.blocker.to_dict() if self.blocker else None,
            "target": self.target.to_dict() if self.target else None,
            "artifacts": _copy_mapping(self.artifacts),
            "operation_log": list(self.operation_log),
            "progress_events": list(self.progress_events),
            "operation_receipts": list(self.operation_receipts),
            "mirror_events": list(self.mirror_events),
        }
