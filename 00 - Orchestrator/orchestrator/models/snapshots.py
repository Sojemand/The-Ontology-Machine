"""Snapshot types and defaults for the orchestrator pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ..policy_store.types import PIPELINE_STAGE_NAMES

STAGE_NAMES = PIPELINE_STAGE_NAMES


def default_stage_statuses() -> dict[str, "StageSnapshot"]:
    from ..integrations import pipeline_stage_names

    return {name: StageSnapshot() for name in pipeline_stage_names()}


@dataclass
class StageSnapshot:
    status: str = "Ready"
    detail: str = ""
    progress_current: int = 0
    progress_total: int = 0
    progress_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineSnapshot:
    total: int = 0
    completed: int = 0
    pending: int = 0
    success: int = 0
    errors: int = 0
    needs_review: int = 0
    retries: int = 0
    current_file: str = ""
    current_attempt: int = 0
    current_route_family: str = ""
    current_optimizer_module: str = ""
    current_interpreter_module: str = ""
    current_intake_reason: str = ""
    is_running: bool = False
    aborted: bool = False
    stage_statuses: dict[str, StageSnapshot] = field(default_factory=default_stage_statuses)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "completed": self.completed,
            "pending": self.pending,
            "success": self.success,
            "errors": self.errors,
            "needs_review": self.needs_review,
            "retries": self.retries,
            "current_file": self.current_file,
            "current_attempt": self.current_attempt,
            "current_route_family": self.current_route_family,
            "current_optimizer_module": self.current_optimizer_module,
            "current_interpreter_module": self.current_interpreter_module,
            "current_intake_reason": self.current_intake_reason,
            "is_running": self.is_running,
            "aborted": self.aborted,
            "stage_statuses": {
                key: value.to_dict() for key, value in self.stage_statuses.items()
            },
        }
