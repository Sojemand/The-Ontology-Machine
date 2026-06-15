from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from semantic_control_kernel.types.base import make_contract_ref_type


@dataclass(frozen=True)
class ArtifactRef:
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ArtifactRef":
        return cls(deepcopy(dict(payload)))

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.payload)


@dataclass(frozen=True)
class TargetIdentity:
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetIdentity":
        return cls(deepcopy(dict(payload)))

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.payload)


@dataclass(frozen=True)
class StateSnapshotIdentity:
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateSnapshotIdentity":
        return cls(deepcopy(dict(payload)))

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.payload)


@dataclass(frozen=True)
class SupportBundleRef:
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SupportBundleRef":
        return cls(deepcopy(dict(payload)))

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.payload)


InterpreterRequestViewVisionRef = make_contract_ref_type(
    "InterpreterRequestViewVisionRef",
    "interpreter_request_view_vision.v1",
    __name__,
)
InterpreterRequestViewFileRef = make_contract_ref_type(
    "InterpreterRequestViewFileRef",
    "interpreter_request_view_file.v1",
    __name__,
)
