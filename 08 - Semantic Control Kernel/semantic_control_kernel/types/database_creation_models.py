from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping, Sequence

from semantic_control_kernel.types.database_creation_support import JsonObject, copy_mapping, copy_sequence


@dataclass(frozen=True)
class DatabaseCreationPlan:
    workflow_run_id: str
    workflow_tool: str
    step_ids: tuple[str, ...]
    initial_state_snapshot_id: str
    target_identity: Mapping[str, Any]
    resume_policy: Mapping[str, Any]

    SCHEMA_VERSION: ClassVar[str] = "kernel.database_creation_plan.v1"

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "workflow_run_id": self.workflow_run_id,
            "workflow_tool": self.workflow_tool,
            "step_ids": list(self.step_ids),
            "initial_state_snapshot_id": self.initial_state_snapshot_id,
            "target_identity": copy_mapping(self.target_identity),
            "resume_policy": copy_mapping(self.resume_policy),
        }


@dataclass(frozen=True)
class StagedSemanticReleaseComponent:
    component_kind: str
    stage_id: str
    artifact_ref: Mapping[str, Any]
    component_identity: Mapping[str, Any]
    fingerprint: str
    source_analysis_refs: tuple[Mapping[str, Any], ...] = ()
    validation_status: str = "validated"

    SCHEMA_VERSION: ClassVar[str] = "kernel.staged_semantic_release_component.v1"

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "component_kind": self.component_kind,
            "stage_id": self.stage_id,
            "artifact_ref": copy_mapping(self.artifact_ref),
            "component_identity": copy_mapping(self.component_identity),
            "fingerprint": self.fingerprint,
            "source_analysis_refs": copy_sequence(self.source_analysis_refs),
            "validation_status": self.validation_status,
        }


@dataclass(frozen=True)
class DefaultSemanticReleaseRef:
    release_id: str
    release_version: str
    release_fingerprint: str
    taxonomy_ref: Mapping[str, Any]
    projection_refs: tuple[Mapping[str, Any], ...]
    source_adapter_receipt_ref: Mapping[str, Any]

    SCHEMA_VERSION: ClassVar[str] = "kernel.default_semantic_release_ref.v1"

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "DefaultSemanticReleaseRef":
        source = payload.get("release_ref") if isinstance(payload.get("release_ref"), Mapping) else payload
        projections = source.get("projection_refs", source.get("projections", ()))
        if not isinstance(projections, Sequence) or isinstance(projections, (str, bytes)):
            projections = ()
        return cls(
            release_id=str(source["release_id"]),
            release_version=str(source["release_version"]),
            release_fingerprint=str(source["release_fingerprint"]),
            taxonomy_ref=copy_mapping(source["taxonomy_ref"]),
            projection_refs=tuple(copy_mapping(item) for item in projections if isinstance(item, Mapping)),
            source_adapter_receipt_ref=copy_mapping(
                source.get("source_adapter_receipt_ref")
                or payload.get("source_adapter_receipt_ref")
                or payload.get("adapter_receipt_ref")
            ),
        )

    @property
    def is_complete(self) -> bool:
        return bool(self.taxonomy_ref and self.projection_refs and self.release_fingerprint)

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "release_id": self.release_id,
            "release_version": self.release_version,
            "release_fingerprint": self.release_fingerprint,
            "taxonomy_ref": copy_mapping(self.taxonomy_ref),
            "projection_refs": copy_sequence(self.projection_refs),
            "source_adapter_receipt_ref": copy_mapping(self.source_adapter_receipt_ref),
        }


@dataclass(frozen=True)
class DatabaseCreationResumeContext:
    workflow_run_id: str
    workflow_tool: str
    last_completed_step_id: str
    next_step_id: str
    target_identity: Mapping[str, Any]
    state_snapshot_id: str
    final_state: str = "unknown"
    target_payload: Mapping[str, Any] = field(default_factory=dict)
    staged_component_refs: tuple[Mapping[str, Any], ...] = ()
    allowed_continuation_workflow_tools: tuple[str, ...] = ()

    SCHEMA_VERSION: ClassVar[str] = "kernel.database_creation_resume_context.v1"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DatabaseCreationResumeContext":
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError(f"Expected {cls.SCHEMA_VERSION}.")
        return cls(
            workflow_run_id=str(payload["workflow_run_id"]),
            workflow_tool=str(payload["workflow_tool"]),
            last_completed_step_id=str(payload["last_completed_step_id"]),
            next_step_id=str(payload["next_step_id"]),
            target_identity=copy_mapping(payload["target_identity"]),
            state_snapshot_id=str(payload["state_snapshot_id"]),
            final_state=str(payload.get("final_state") or "unknown"),
            target_payload=copy_mapping(payload.get("target_payload")),
            staged_component_refs=tuple(copy_mapping(item) for item in payload.get("staged_component_refs", ()) if isinstance(item, Mapping)),
            allowed_continuation_workflow_tools=tuple(str(item) for item in payload.get("allowed_continuation_workflow_tools", ())),
        )

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "workflow_run_id": self.workflow_run_id,
            "workflow_tool": self.workflow_tool,
            "last_completed_step_id": self.last_completed_step_id,
            "next_step_id": self.next_step_id,
            "target_identity": copy_mapping(self.target_identity),
            "state_snapshot_id": self.state_snapshot_id,
            "final_state": self.final_state,
            "target_payload": copy_mapping(self.target_payload),
            "staged_component_refs": copy_sequence(self.staged_component_refs),
            "allowed_continuation_workflow_tools": list(self.allowed_continuation_workflow_tools),
        }


@dataclass(frozen=True)
class DatabaseCreationBlocker:
    blocker_code: str
    step_id: str
    function_or_route: str
    recovery_state_class: str
    user_visible_summary: str
    diagnostics: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> JsonObject:
        return {
            "blocker_code": self.blocker_code,
            "step_id": self.step_id,
            "function_or_route": self.function_or_route,
            "recovery_state_class": self.recovery_state_class,
            "user_visible_summary": self.user_visible_summary,
            "diagnostics": copy_sequence(self.diagnostics),
        }
