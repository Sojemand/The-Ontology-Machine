from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.types.base import make_contract_type


DatabaseRebuildManifest = make_contract_type(
    "DatabaseRebuildManifest",
    "kernel.database_rebuild_manifest.v1",
    __name__,
)

JsonObject = dict[str, Any]

def _canonical_path_text(path: str | os.PathLike[str]) -> str:
    resolved = Path(path).resolve(strict=False)
    text = str(resolved).replace("\\", "/")
    anchor = resolved.anchor.replace("\\", "/").rstrip("/")
    if anchor and text.rstrip("/") != anchor:
        text = text.rstrip("/")
    if os.name == "nt" or resolved.drive:
        text = text.casefold()
    return text


def _path_hash(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(_canonical_path_text(path).encode("utf-8")).hexdigest()[:24]


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


REBUILD_MANIFEST_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "rebuild_run_id",
    "workflow_run_id",
    "artifact_root",
    "target_database_path",
    "loaded_semantic_release_id",
    "loaded_semantic_release_version",
    "loaded_release_fingerprint",
    "corpus_builder_run_ref",
    "embedding_policy",
    "embedding_result",
    "activation_receipt_id",
    "record_count",
    "created_at",
    "finalized_at",
    "manifest_fingerprint",
)


@dataclass(frozen=True)
class RebuildWorkflowBlocker:
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


@dataclass
class RebuildWorkflowExecution:
    workflow_run_id: str
    workflow_tool: str
    rebuild_run_id: str
    state_root: Any
    artifact_root: str
    target_database_path: str
    status: str = "running"
    final_state: str = "unknown"
    completed_step_ids: list[str] = field(default_factory=list)
    blocked_step_id: str | None = None
    blocker: RebuildWorkflowBlocker | None = None
    progress_events: list[JsonObject] = field(default_factory=list)
    operation_receipts: list[JsonObject] = field(default_factory=list)
    mirror_events: list[JsonObject] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    operation_log: list[str] = field(default_factory=list)
    resume_state: JsonObject | None = None

    @property
    def target_identity(self) -> JsonObject:
        artifact_root_path_hash = _path_hash(self.artifact_root)
        database_path_hash = _path_hash(self.target_database_path)
        return {
            "schema_version": "state.target_identity.v1",
            "artifact_root_path_hash": artifact_root_path_hash,
            "database_path_hash": database_path_hash,
            "workflow_run_id": self.workflow_run_id,
            "lock_scope": "database_rebuild",
            "target_hash": _stable_hash(f"{artifact_root_path_hash}:{database_path_hash}:{self.workflow_run_id}"),
            "created_from": "rebuild.workflow",
        }

    def to_dict(self) -> JsonObject:
        return {
            "artifact_root": self.artifact_root,
            "artifacts": dict(self.artifacts),
            "blocked_step_id": self.blocked_step_id,
            "blocker": self.blocker.to_dict() if self.blocker else None,
            "completed_step_ids": list(self.completed_step_ids),
            "final_state": self.final_state,
            "mirror_events": list(self.mirror_events),
            "operation_log": list(self.operation_log),
            "operation_receipts": list(self.operation_receipts),
            "progress_events": list(self.progress_events),
            "rebuild_run_id": self.rebuild_run_id,
            "resume_state": dict(self.resume_state or {}),
            "status": self.status,
            "target_database_path": self.target_database_path,
            "workflow_run_id": self.workflow_run_id,
            "workflow_tool": self.workflow_tool,
        }


def release_identity_from_payload(payload: Mapping[str, Any]) -> JsonObject:
    return {
        "loaded_release_path": str(payload.get("release_path") or payload.get("loaded_release_path") or payload.get("source_path") or ""),
        "loaded_release_fingerprint": str(payload.get("release_fingerprint") or payload.get("loaded_release_fingerprint") or payload.get("fingerprint") or ""),
        "loaded_semantic_release_id": str(payload.get("release_id") or payload.get("semantic_release_id") or payload.get("loaded_semantic_release_id") or ""),
        "loaded_semantic_release_version": str(payload.get("release_version") or payload.get("semantic_release_version") or payload.get("loaded_semantic_release_version") or ""),
        "runtime_locale": str(payload.get("runtime_locale") or payload.get("loaded_runtime_locale") or ""),
    }
