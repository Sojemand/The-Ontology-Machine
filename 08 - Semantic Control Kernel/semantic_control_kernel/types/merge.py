from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.base import make_contract_type
from semantic_control_kernel.types.merge_contract_fields import (
    MERGE_COLLISION_REQUIRED_FIELDS,
    MERGE_ID_MAP_REQUIRED_FIELDS,
    MERGE_SELECTION_REQUIRED_FIELDS,
    MERGE_SOURCE_REQUIRED_FIELDS,
    PROJECTION_MERGE_MODE_DEFAULT,
    PROJECTION_MERGE_MODE_PRESERVE,
    PROJECTION_MERGE_MODE_SINGLE,
    PROJECTION_MERGE_MODE_VALUES,
    SOURCE_IDENTITY_ORIGINS,
)


DatabaseMergeSelection = make_contract_type(
    "DatabaseMergeSelection",
    "kernel.database_merge_selection.v1",
    __name__,
)
DatabaseMergeCollisionManifest = make_contract_type(
    "DatabaseMergeCollisionManifest",
    "kernel.database_merge_collision_manifest.v1",
    __name__,
)
DatabaseMergeIdMap = make_contract_type("DatabaseMergeIdMap", "kernel.database_merge_id_map.v1", __name__)


JsonObject = dict[str, Any]

@dataclass(frozen=True)
class MergeWorkflowBlocker:
    blocker_code: str
    step_id: str
    function_or_route: str
    recovery_state_class: str
    user_visible_summary: str
    diagnostics: tuple[JsonObject, ...] = ()

    def to_dict(self) -> JsonObject:
        return {
            "blocker_code": self.blocker_code,
            "diagnostics": [dict(item) for item in self.diagnostics],
            "function_or_route": self.function_or_route,
            "recovery_state_class": self.recovery_state_class,
            "step_id": self.step_id,
            "user_visible_summary": self.user_visible_summary,
        }


@dataclass(frozen=True)
class SourceDatabaseDescriptor:
    source_database_id: str
    source_database_path: str
    source_artifact_root: str | None
    source_state: str
    source_semantic_release_id: str
    source_semantic_release_version: str
    source_release_fingerprint: str
    source_database_fingerprint: str
    source_artifact_tree_fingerprint: str
    source_identity_origin: str
    durable_source_database_id: str | None = None
    materialization_refs: tuple[JsonObject, ...] = ()
    source_release_ref: JsonObject = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SourceDatabaseDescriptor":
        refs = payload.get("materialization_refs")
        return cls(
            source_database_id=str(payload.get("source_database_id", "")),
            source_database_path=str(payload.get("source_database_path", "")),
            source_artifact_root=_optional_text(payload.get("source_artifact_root")),
            source_state=str(payload.get("source_state", "")),
            source_semantic_release_id=str(payload.get("source_semantic_release_id", "")),
            source_semantic_release_version=str(payload.get("source_semantic_release_version", "")),
            source_release_fingerprint=str(payload.get("source_release_fingerprint", "")),
            source_database_fingerprint=str(payload.get("source_database_fingerprint", "")),
            source_artifact_tree_fingerprint=str(payload.get("source_artifact_tree_fingerprint", "")),
            source_identity_origin=str(payload.get("source_identity_origin", "")),
            durable_source_database_id=_optional_text(payload.get("durable_source_database_id")),
            materialization_refs=tuple(dict(item) for item in refs if isinstance(item, Mapping)) if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes)) else (),
            source_release_ref=dict(payload.get("source_release_ref") or {}) if isinstance(payload.get("source_release_ref"), Mapping) else {},
        )

    def to_selection_entry(self) -> JsonObject:
        return {
            "source_artifact_root": self.source_artifact_root,
            "source_artifact_tree_fingerprint": self.source_artifact_tree_fingerprint,
            "source_database_fingerprint": self.source_database_fingerprint,
            "source_database_id": self.source_database_id,
            "source_database_path": self.source_database_path,
            "source_identity_origin": self.source_identity_origin,
            "source_release_fingerprint": self.source_release_fingerprint,
            "source_release_ref": dict(self.source_release_ref),
            "source_semantic_release_id": self.source_semantic_release_id,
            "source_semantic_release_version": self.source_semantic_release_version,
            "source_state": self.source_state,
        }

    @property
    def is_empty(self) -> bool:
        return self.source_state == "empty"

    @property
    def is_filled(self) -> bool:
        return self.source_state == "filled"


@dataclass
class MergeWorkflowExecution:
    workflow_run_id: str
    workflow_tool: str
    merge_run_id: str
    state_root: Any
    status: str = "running"
    final_state: str = "unknown"
    completed_step_ids: list[str] = field(default_factory=list)
    blocked_step_id: str | None = None
    blocker: MergeWorkflowBlocker | None = None
    selection: JsonObject | None = None
    progress_events: list[JsonObject] = field(default_factory=list)
    operation_receipts: list[JsonObject] = field(default_factory=list)
    mirror_events: list[JsonObject] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    operation_log: list[str] = field(default_factory=list)
    resume_state: JsonObject | None = None

    def to_dict(self) -> JsonObject:
        return {
            "artifacts": dict(self.artifacts),
            "blocked_step_id": self.blocked_step_id,
            "blocker": self.blocker.to_dict() if self.blocker else None,
            "completed_step_ids": list(self.completed_step_ids),
            "final_state": self.final_state,
            "merge_run_id": self.merge_run_id,
            "mirror_events": list(self.mirror_events),
            "operation_log": list(self.operation_log),
            "operation_receipts": list(self.operation_receipts),
            "progress_events": list(self.progress_events),
            "resume_state": dict(self.resume_state or {}),
            "selection": dict(self.selection or {}),
            "status": self.status,
            "workflow_run_id": self.workflow_run_id,
            "workflow_tool": self.workflow_tool,
        }


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
