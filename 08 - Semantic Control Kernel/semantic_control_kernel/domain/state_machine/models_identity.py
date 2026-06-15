from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.models_support import copy_mapping


@dataclass(frozen=True)
class TargetSelector:
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSelector":
        return cls(copy_mapping(payload))

    def to_dict(self) -> dict[str, Any]:
        return copy_mapping(self.payload)


@dataclass(frozen=True)
class TargetIdentity:
    database_path_hash: str
    artifact_root_path_hash: str
    lock_scope: str
    target_hash: str
    created_from: str
    database_id: str | None = None
    release_fingerprint: str | None = None
    semantic_release_identity_hash: str | None = None
    taxonomy_fingerprint: str | None = None
    projection_set_hash: str | None = None
    pipeline_batch_id: str | None = None
    source_database_set_hash: str | None = None

    SCHEMA_VERSION = "state.target_identity.v1"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetIdentity":
        data = copy_mapping(payload)
        return cls(
            database_path_hash=str(data.get("database_path_hash", "")),
            artifact_root_path_hash=str(data.get("artifact_root_path_hash", "")),
            lock_scope=str(data.get("lock_scope", "target")),
            target_hash=str(data.get("target_hash", "")),
            created_from=str(data.get("created_from", "payload")),
            database_id=data.get("database_id"),
            release_fingerprint=data.get("release_fingerprint"),
            semantic_release_identity_hash=data.get("semantic_release_identity_hash"),
            taxonomy_fingerprint=data.get("taxonomy_fingerprint"),
            projection_set_hash=data.get("projection_set_hash"),
            pipeline_batch_id=data.get("pipeline_batch_id"),
            source_database_set_hash=data.get("source_database_set_hash"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "database_path_hash": self.database_path_hash,
            "artifact_root_path_hash": self.artifact_root_path_hash,
            "lock_scope": self.lock_scope,
            "target_hash": self.target_hash,
            "created_from": self.created_from,
        }
        optional = {
            "database_id": self.database_id,
            "release_fingerprint": self.release_fingerprint,
            "semantic_release_identity_hash": self.semantic_release_identity_hash,
            "taxonomy_fingerprint": self.taxonomy_fingerprint,
            "projection_set_hash": self.projection_set_hash,
            "pipeline_batch_id": self.pipeline_batch_id,
            "source_database_set_hash": self.source_database_set_hash,
        }
        payload.update({key: value for key, value in optional.items() if value})
        return payload
