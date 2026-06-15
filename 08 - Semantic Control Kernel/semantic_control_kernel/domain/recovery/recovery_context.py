from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


@dataclass(frozen=True)
class RecoveryContext:
    workflow_run_id: str
    workflow_tool: str
    failed_kernel_step: str
    target_identity: Mapping[str, Any]
    state_snapshot_identity: Mapping[str, Any]
    detected_by: str = "SemanticExceptionHandler"
    blocked_functions: tuple[str, ...] = ()
    support_refs: tuple[Mapping[str, Any], ...] = ()
    resume_state_ref: Mapping[str, Any] | None = None
    lock_refs: tuple[str, ...] = ()
    cause_context: Mapping[str, Any] = field(default_factory=dict)

    def target_payload(self) -> dict[str, Any]:
        return _copy_mapping(self.target_identity)

    def snapshot_payload(self) -> dict[str, Any]:
        return _copy_mapping(self.state_snapshot_identity)
