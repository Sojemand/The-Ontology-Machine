from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.models_enums import BlockerSeverity
from semantic_control_kernel.domain.state_machine.models_support import copy_mapping, tuple_of_str


@dataclass(frozen=True)
class StateBlocker:
    blocker_code: str
    function_or_route: str
    recovery_state_class: str
    severity: str
    required_state: str
    actual_state: str
    target_identity: dict[str, Any]
    state_snapshot_id: str
    evidence_refs: tuple[str, ...]
    user_visible_summary: str
    technical_detail: str

    SCHEMA_VERSION = "state.blocker.v1"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateBlocker":
        data = copy_mapping(payload)
        return cls(
            blocker_code=str(data["blocker_code"]),
            function_or_route=str(data.get("function_or_route", "")),
            recovery_state_class=str(data["recovery_state_class"]),
            severity=str(data.get("severity", BlockerSeverity.RECOVERABLE_ERROR.value)),
            required_state=str(data.get("required_state", "")),
            actual_state=str(data.get("actual_state", "")),
            target_identity=copy_mapping(data.get("target_identity")),
            state_snapshot_id=str(data.get("state_snapshot_id", "")),
            evidence_refs=tuple_of_str(data.get("evidence_refs")),
            user_visible_summary=str(data.get("user_visible_summary", "")),
            technical_detail=str(data.get("technical_detail", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "blocker_code": self.blocker_code,
            "function_or_route": self.function_or_route,
            "recovery_state_class": self.recovery_state_class,
            "severity": self.severity,
            "required_state": self.required_state,
            "actual_state": self.actual_state,
            "target_identity": copy_mapping(self.target_identity),
            "state_snapshot_id": self.state_snapshot_id,
            "evidence_refs": list(self.evidence_refs),
            "user_visible_summary": self.user_visible_summary,
            "technical_detail": self.technical_detail,
        }


@dataclass(frozen=True)
class EligibilityResult:
    function_or_route: str
    status: str
    state_snapshot_id: str
    target_identity: dict[str, Any]
    post_state_when_allowed: str | None
    blockers: tuple[StateBlocker, ...] = ()
    required_confirmation_gate: str | None = None

    SCHEMA_VERSION = "state.eligibility_result.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "function_or_route": self.function_or_route,
            "status": self.status,
            "state_snapshot_id": self.state_snapshot_id,
            "target_identity": copy_mapping(self.target_identity),
            "post_state_when_allowed": self.post_state_when_allowed,
            "blockers": [blocker.to_dict() for blocker in self.blockers],
            "required_confirmation_gate": self.required_confirmation_gate,
        }
