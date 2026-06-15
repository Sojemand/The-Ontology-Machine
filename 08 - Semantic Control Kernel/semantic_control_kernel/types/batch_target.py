from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Mapping, Sequence

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.batch_common import JsonObject, _copy_mapping, _copy_sequence


@dataclass(frozen=True)
class PipelineRunTarget:
    workflow_run_id: str
    database_path: str
    database_path_hash: str
    database_id: str
    database_fingerprint: str
    artifact_root_path: str
    artifact_root_path_hash: str
    artifact_root_fingerprint: str
    input_path: str
    documents_path: str
    corpus_path: str
    semantic_release_path: str
    database_emptiness: str
    semantic_release_state: str
    active_release_ref: Mapping[str, Any]
    taxonomy_ref: Mapping[str, Any]
    projection_refs: Sequence[Mapping[str, Any]]
    state_snapshot_id: str
    binding_ref: Mapping[str, Any] = field(default_factory=dict)

    SCHEMA_VERSION: ClassVar[str] = "kernel.pipeline_run_target.v1"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PipelineRunTarget":
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError(f"Expected {cls.SCHEMA_VERSION}.")
        return cls(
            workflow_run_id=str(payload["workflow_run_id"]),
            database_path=str(payload["database_path"]),
            database_path_hash=str(payload["database_path_hash"]),
            database_id=str(payload["database_id"]),
            database_fingerprint=str(payload["database_fingerprint"]),
            artifact_root_path=str(payload["artifact_root_path"]),
            artifact_root_path_hash=str(payload["artifact_root_path_hash"]),
            artifact_root_fingerprint=str(payload["artifact_root_fingerprint"]),
            input_path=str(payload["input_path"]),
            documents_path=str(payload["documents_path"]),
            corpus_path=str(payload["corpus_path"]),
            semantic_release_path=str(payload["semantic_release_path"]),
            database_emptiness=str(payload["database_emptiness"]),
            semantic_release_state=str(payload["semantic_release_state"]),
            active_release_ref=_copy_mapping(payload["active_release_ref"]),
            taxonomy_ref=_copy_mapping(payload["taxonomy_ref"]),
            projection_refs=tuple(_copy_mapping(item) for item in payload.get("projection_refs", ()) if isinstance(item, Mapping)),
            state_snapshot_id=str(payload["state_snapshot_id"]),
            binding_ref=_copy_mapping(payload.get("binding_ref")),
        )

    @property
    def target_identity(self) -> JsonObject:
        return {
            "schema_version": "state.target_identity.v1",
            "database_path_hash": self.database_path_hash,
            "artifact_root_path_hash": self.artifact_root_path_hash,
            "state_snapshot_id": self.state_snapshot_id,
            "lock_scope": "pipeline_run",
            "target_hash": stable_hash(f"{self.artifact_root_path_hash}:{self.database_path_hash}:{self.state_snapshot_id}"),
            "created_from": self.SCHEMA_VERSION,
        }

    @property
    def release_fingerprint(self) -> str:
        return str(self.active_release_ref.get("release_fingerprint", ""))

    @property
    def semantic_release_id(self) -> str:
        return str(self.active_release_ref.get("semantic_release_id") or self.active_release_ref.get("release_id", ""))

    @property
    def semantic_release_version(self) -> str:
        return str(self.active_release_ref.get("semantic_release_version") or self.active_release_ref.get("release_version", ""))

    @property
    def taxonomy_id(self) -> str:
        return str(self.taxonomy_ref.get("taxonomy_id", ""))

    @property
    def taxonomy_version(self) -> str:
        return str(self.taxonomy_ref.get("taxonomy_version", ""))

    @property
    def taxonomy_fingerprint(self) -> str:
        return str(self.taxonomy_ref.get("taxonomy_fingerprint", ""))

    @property
    def has_exact_binding_proof(self) -> bool:
        binding = self.binding_ref
        if not binding or binding.get("binding_status") not in {None, "verified", "active"}:
            return False
        return binding.get("database_path_hash") == self.database_path_hash and binding.get("artifact_root_path_hash") == self.artifact_root_path_hash

    @property
    def artifact_root(self) -> Path:
        return Path(self.artifact_root_path)

    def active_database_manifest_ref(self) -> JsonObject:
        return {
            "database_id": self.database_id,
            "database_path": self.database_path,
            "database_fingerprint": self.database_fingerprint,
            "database_path_hash": self.database_path_hash,
        }

    def artifact_root_manifest_ref(self) -> JsonObject:
        return {
            "artifact_root_path": self.artifact_root_path,
            "artifact_root_fingerprint": self.artifact_root_fingerprint,
            "input_path": self.input_path,
            "documents_path": self.documents_path,
            "corpus_path": self.corpus_path,
            "semantic_release_path": self.semantic_release_path,
        }

    def semantic_release_manifest_ref(self) -> JsonObject:
        return {
            "semantic_release_id": self.semantic_release_id,
            "semantic_release_version": self.semantic_release_version,
            "release_fingerprint": self.release_fingerprint,
            "taxonomy_id": self.taxonomy_id,
            "taxonomy_version": self.taxonomy_version,
            "taxonomy_fingerprint": self.taxonomy_fingerprint,
        }

    def projection_manifest_refs(self) -> list[JsonObject]:
        return [
            {
                "projection_id": str(projection.get("projection_id", "")),
                "projection_fingerprint": str(projection.get("projection_fingerprint", "")),
            }
            for projection in self.projection_refs
        ]

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "workflow_run_id": self.workflow_run_id,
            "database_path": self.database_path,
            "database_path_hash": self.database_path_hash,
            "database_id": self.database_id,
            "database_fingerprint": self.database_fingerprint,
            "artifact_root_path": self.artifact_root_path,
            "artifact_root_path_hash": self.artifact_root_path_hash,
            "artifact_root_fingerprint": self.artifact_root_fingerprint,
            "input_path": self.input_path,
            "documents_path": self.documents_path,
            "corpus_path": self.corpus_path,
            "semantic_release_path": self.semantic_release_path,
            "database_emptiness": self.database_emptiness,
            "semantic_release_state": self.semantic_release_state,
            "active_release_ref": _copy_mapping(self.active_release_ref),
            "taxonomy_ref": _copy_mapping(self.taxonomy_ref),
            "projection_refs": _copy_sequence(self.projection_refs),
            "state_snapshot_id": self.state_snapshot_id,
            "binding_ref": _copy_mapping(self.binding_ref),
        }
