from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.database_creation import (
    DatabaseCreationBlocker,
    DatabaseCreationResumeContext,
    DatabaseCreationTarget,
)


class CreationInteractionPort(Protocol):
    def collect_creation_target(self, *, workflow_tool: str, workflow_run_id: str) -> DatabaseCreationTarget | None:
        ...

    def select_sample_files(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
        purpose: str,
        target: DatabaseCreationTarget | None,
    ) -> tuple[Mapping[str, Any], ...]:
        ...

    def resolve_taxonomy_ref(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
        target: DatabaseCreationTarget | None,
        state: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        ...


class EmptyInteractionPort:
    def collect_creation_target(self, *, workflow_tool: str, workflow_run_id: str) -> DatabaseCreationTarget | None:
        return None

    def select_sample_files(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
        purpose: str,
        target: DatabaseCreationTarget | None,
    ) -> tuple[Mapping[str, Any], ...]:
        return ()

    def resolve_taxonomy_ref(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
        target: DatabaseCreationTarget | None,
        state: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        return None


@dataclass
class DatabaseCreationExecution:
    workflow_run_id: str
    workflow_tool: str
    state_root: Path
    target: DatabaseCreationTarget | None = None
    final_state: str = "unknown"
    status: str = "running"
    completed_step_ids: list[str] = field(default_factory=list)
    completed_step_ids_at_run_start: list[str] = field(default_factory=list)
    satisfied_precondition_step_ids: list[str] = field(default_factory=list)
    blocked_step_id: str | None = None
    blocker: DatabaseCreationBlocker | None = None
    resume_context: DatabaseCreationResumeContext | None = None
    progress_events: list[dict[str, Any]] = field(default_factory=list)
    operation_receipts: list[dict[str, Any]] = field(default_factory=list)
    mirror_events: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    operation_log: list[str] = field(default_factory=list)
    _sequence_index: int = 0

    @property
    def target_identity(self) -> dict[str, Any]:
        if self.target is None:
            return {}
        return self.target.target_identity

    @property
    def state_snapshot_id(self) -> str:
        return stable_hash(f"{self.workflow_run_id}:{self.final_state}:{','.join(self.completed_step_ids)}")

    def to_dict(self) -> dict[str, Any]:
        completed_at_start = set(self.completed_step_ids_at_run_start)
        return {
            "workflow_run_id": self.workflow_run_id,
            "workflow_tool": self.workflow_tool,
            "status": self.status,
            "final_state": self.final_state,
            "completed_step_ids": list(self.completed_step_ids),
            "completed_step_ids_at_run_start": list(self.completed_step_ids_at_run_start),
            "completed_step_ids_this_run": [
                step_id for step_id in self.completed_step_ids if step_id not in completed_at_start
            ],
            "satisfied_precondition_step_ids": list(self.satisfied_precondition_step_ids),
            "blocked_step_id": self.blocked_step_id,
            "blocker": self.blocker.to_dict() if self.blocker else None,
            "resume_context": self.resume_context.to_dict() if self.resume_context else None,
            "target": self.target.to_dict() if self.target else None,
            "progress_events": list(self.progress_events),
            "operation_receipts": list(self.operation_receipts),
            "mirror_events": list(self.mirror_events),
            "artifacts": dict(self.artifacts),
            "operation_log": list(self.operation_log),
        }
