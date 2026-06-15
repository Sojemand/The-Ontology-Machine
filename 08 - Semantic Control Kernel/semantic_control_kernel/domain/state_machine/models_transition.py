from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.models_support import copy_mapping, tuple_of_str


@dataclass(frozen=True)
class TransitionRule:
    rule_id: str
    function_or_route: str
    required_state: tuple[str, ...]
    required_state_text: str
    required_inputs: tuple[str, ...]
    required_evidence: tuple[str, ...]
    writes_or_mutates: str
    post_state: str
    post_state_text: str
    blocks_if: tuple[str, ...]
    confirmation_gate: str
    default_recovery_states: tuple[str, ...]

    SCHEMA_VERSION = "state.transition_rule.v1"

    @property
    def deprecated(self) -> bool:
        return "deprecated_function" in self.blocks_if

    @property
    def mutates_state_or_artifacts(self) -> bool:
        text = self.writes_or_mutates.strip().casefold()
        return text not in {"", "none", "validation result or blocker"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "rule_id": self.rule_id,
            "function_or_route": self.function_or_route,
            "required_state": list(self.required_state),
            "required_state_text": self.required_state_text,
            "required_inputs": list(self.required_inputs),
            "required_evidence": list(self.required_evidence),
            "writes_or_mutates": self.writes_or_mutates,
            "post_state": self.post_state,
            "post_state_text": self.post_state_text,
            "blocks_if": list(self.blocks_if),
            "confirmation_gate": self.confirmation_gate,
            "default_recovery_states": list(self.default_recovery_states),
        }


@dataclass(frozen=True)
class TransitionInputRefs:
    present_inputs: frozenset[str] | None = None
    evidence_refs: tuple[str, ...] = ()
    confirmation_receipts: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    explicit_blockers: tuple[str, ...] = ()
    source_database_emptiness: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def for_rule(cls, rule: TransitionRule, **metadata: Any) -> "TransitionInputRefs":
        known = {
            "confirmation_receipts": metadata.pop("confirmation_receipts", {}),
            "explicit_blockers": metadata.pop("explicit_blockers", ()),
            "source_database_emptiness": metadata.pop("source_database_emptiness", ()),
        }
        return cls(present_inputs=frozenset(rule.required_inputs), metadata=metadata, **known)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransitionInputRefs":
        data = copy_mapping(payload)
        present = data.get("present_inputs")
        return cls(
            present_inputs=frozenset(str(item) for item in present) if present is not None else None,
            evidence_refs=tuple_of_str(data.get("evidence_refs")),
            confirmation_receipts=copy_mapping(data.get("confirmation_receipts")),
            explicit_blockers=tuple_of_str(data.get("explicit_blockers")),
            source_database_emptiness=tuple_of_str(data.get("source_database_emptiness")),
            metadata=copy_mapping(data.get("metadata")),
        )

    def has_input(self, input_name: str) -> bool:
        if self.present_inputs is None:
            return False
        return input_name in self.present_inputs


@dataclass(frozen=True)
class StateSpecDisagreement:
    workflow_spec: str
    workflow_route: str
    step_name: str
    state_table_rule_id: str
    workflow_claim: str
    state_table_claim: str
    required_correction: str

    def to_dict(self) -> dict[str, str]:
        return {
            "workflow_spec": self.workflow_spec,
            "workflow_route": self.workflow_route,
            "step_name": self.step_name,
            "state_table_rule_id": self.state_table_rule_id,
            "workflow_claim": self.workflow_claim,
            "state_table_claim": self.state_table_claim,
            "required_correction": self.required_correction,
        }
