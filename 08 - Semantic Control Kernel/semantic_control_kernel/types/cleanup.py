from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, ClassVar, Mapping, Sequence


JsonObject = dict[str, Any]


def _copy_mapping(value: Mapping[str, Any] | None = None) -> JsonObject:
    return deepcopy(dict(value or {}))


def _copy_sequence(value: Sequence[Any] | None = None) -> list[Any]:
    return deepcopy(list(value or ()))


@dataclass(frozen=True)
class DatabaseResetManifest:
    workflow_run_id: str
    reset_manifest_id: str
    target_identity_before: Mapping[str, Any]
    target_identity_after: Mapping[str, Any]
    preserved_release_ref: Mapping[str, Any]
    prior_semantic_release_state: str
    post_reset_semantic_release_state: str
    superseded_batch_refs: Sequence[Mapping[str, Any]]
    confirmation_receipt_ref: Mapping[str, Any]
    reset_adapter_receipt_ref: Mapping[str, Any]
    empty_state_proven: bool

    SCHEMA_VERSION: ClassVar[str] = "kernel.database_reset_manifest.v1"

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "workflow_run_id": self.workflow_run_id,
            "reset_manifest_id": self.reset_manifest_id,
            "target_identity_before": _copy_mapping(self.target_identity_before),
            "target_identity_after": _copy_mapping(self.target_identity_after),
            "preserved_release_ref": _copy_mapping(self.preserved_release_ref),
            "prior_semantic_release_state": self.prior_semantic_release_state,
            "post_reset_semantic_release_state": self.post_reset_semantic_release_state,
            "superseded_batch_refs": _copy_sequence(self.superseded_batch_refs),
            "confirmation_receipt_ref": _copy_mapping(self.confirmation_receipt_ref),
            "reset_adapter_receipt_ref": _copy_mapping(self.reset_adapter_receipt_ref),
            "empty_state_proven": self.empty_state_proven,
        }
