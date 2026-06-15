from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Mapping

from semantic_control_kernel.repository.paths import path_hash, stable_hash
from semantic_control_kernel.types.database_creation_support import JsonObject, copy_mapping, normalize_database_name, path_text


@dataclass(frozen=True)
class DatabaseCreationTarget:
    artifact_root_parent: str
    artifact_root_name: str
    database_name: str
    artifact_root_path: str
    corpus_path: str
    input_path: str
    semantic_release_path: str
    database_path: str
    path_hashes: Mapping[str, str]

    SCHEMA_VERSION: ClassVar[str] = "kernel.database_creation_target.v1"

    @classmethod
    def from_selection(
        cls,
        *,
        artifact_root_parent: str | os.PathLike[str],
        artifact_root_name: str,
        database_name: str,
    ) -> "DatabaseCreationTarget":
        root_name = str(artifact_root_name).strip()
        if not root_name or root_name in {".", ".."}:
            raise ValueError("artifact_root_name must be a non-empty folder name.")
        if any(separator and separator in root_name for separator in (os.sep, os.altsep)):
            raise ValueError("artifact_root_name must not contain path separators.")
        db_name = normalize_database_name(database_name)
        parent = Path(artifact_root_parent).resolve(strict=False)
        artifact_root = parent / root_name
        corpus_path = artifact_root / "Corpus"
        input_path = artifact_root / "Input"
        semantic_release_path = artifact_root / "Semantic Release"
        database_path = corpus_path / f"{db_name}.db"
        return cls(
            artifact_root_parent=path_text(parent),
            artifact_root_name=root_name,
            database_name=db_name,
            artifact_root_path=path_text(artifact_root),
            corpus_path=path_text(corpus_path),
            input_path=path_text(input_path),
            semantic_release_path=path_text(semantic_release_path),
            database_path=path_text(database_path),
            path_hashes={
                "artifact_root_path_hash": path_hash(artifact_root),
                "corpus_path_hash": path_hash(corpus_path),
                "input_path_hash": path_hash(input_path),
                "semantic_release_path_hash": path_hash(semantic_release_path),
                "database_path_hash": path_hash(database_path),
            },
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DatabaseCreationTarget":
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError(f"Expected {cls.SCHEMA_VERSION}.")
        return cls(
            artifact_root_parent=str(payload["artifact_root_parent"]),
            artifact_root_name=str(payload["artifact_root_name"]),
            database_name=str(payload["database_name"]),
            artifact_root_path=str(payload["artifact_root_path"]),
            corpus_path=str(payload["corpus_path"]),
            input_path=str(payload["input_path"]),
            semantic_release_path=str(payload["semantic_release_path"]),
            database_path=str(payload["database_path"]),
            path_hashes=copy_mapping(payload.get("path_hashes")),
        )

    @property
    def target_identity(self) -> JsonObject:
        database_path_hash = self.path_hashes["database_path_hash"]
        artifact_root_path_hash = self.path_hashes["artifact_root_path_hash"]
        return {
            "schema_version": "state.target_identity.v1",
            "database_path_hash": database_path_hash,
            "artifact_root_path_hash": artifact_root_path_hash,
            "lock_scope": "database_creation",
            "target_hash": stable_hash(f"{artifact_root_path_hash}:{database_path_hash}"),
            "created_from": self.SCHEMA_VERSION,
        }

    def canonical_paths(self) -> JsonObject:
        return {
            "artifact_root_path": self.artifact_root_path,
            "corpus_path": self.corpus_path,
            "input_path": self.input_path,
            "documents_path": str(Path(self.artifact_root_path) / "Documents"),
            "error_cases_path": str(Path(self.artifact_root_path) / "Error Cases"),
            "semantic_release_path": self.semantic_release_path,
            "database_path": self.database_path,
        }

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "artifact_root_parent": self.artifact_root_parent,
            "artifact_root_name": self.artifact_root_name,
            "database_name": self.database_name,
            "artifact_root_path": self.artifact_root_path,
            "corpus_path": self.corpus_path,
            "input_path": self.input_path,
            "semantic_release_path": self.semantic_release_path,
            "database_path": self.database_path,
            "path_hashes": dict(self.path_hashes),
        }
