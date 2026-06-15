from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.models_identity import TargetSelector
from semantic_control_kernel.domain.state_machine.models_support import copy_mapping


@dataclass(frozen=True)
class StateEvidenceRef:
    evidence_ref_id: str
    source: str
    kind: str
    target_identity: dict[str, Any]
    payload_ref: dict[str, Any]
    observed_at: str
    trust_class: str

    SCHEMA_VERSION = "state.evidence_ref.v1"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateEvidenceRef":
        data = copy_mapping(payload)
        return cls(
            evidence_ref_id=str(data["evidence_ref_id"]),
            source=str(data["source"]),
            kind=str(data["kind"]),
            target_identity=copy_mapping(data.get("target_identity")),
            payload_ref=copy_mapping(data.get("payload_ref")),
            observed_at=str(data.get("observed_at", "")),
            trust_class=str(data["trust_class"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "evidence_ref_id": self.evidence_ref_id,
            "source": self.source,
            "kind": self.kind,
            "target_identity": copy_mapping(self.target_identity),
            "payload_ref": copy_mapping(self.payload_ref),
            "observed_at": self.observed_at,
            "trust_class": self.trust_class,
        }


@dataclass(frozen=True)
class StateEvidenceBundle:
    evidence_bundle_id: str
    created_at: str
    target_selector: TargetSelector
    evidence_refs: tuple[StateEvidenceRef, ...] = ()

    SCHEMA_VERSION = "state.evidence_bundle.v1"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateEvidenceBundle":
        data = copy_mapping(payload)
        return cls(
            evidence_bundle_id=str(data["evidence_bundle_id"]),
            created_at=str(data["created_at"]),
            target_selector=TargetSelector.from_dict(data.get("target_selector", {})),
            evidence_refs=tuple(StateEvidenceRef.from_dict(item) for item in data.get("evidence_refs", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "evidence_bundle_id": self.evidence_bundle_id,
            "created_at": self.created_at,
            "target_selector": self.target_selector.to_dict(),
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
        }
