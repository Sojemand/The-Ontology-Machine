"""Command dataclasses for semantic release contract actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticStatusCommand:
    corpus_db_path: str | None = None


@dataclass(frozen=True)
class ReadActiveSemanticReleaseCommand:
    corpus_db_path: str | None = None


@dataclass(frozen=True)
class LoadSemanticReleaseCommand:
    release_path: str
    corpus_db_path: str | None = None
    write_global_mirrors: bool = True


@dataclass(frozen=True)
class SemanticAuditCommand:
    corpus_db_path: str | None = None


@dataclass(frozen=True)
class BackfillStaleCommand:
    corpus_db_path: str | None = None
    document_ids: tuple[str, ...] = ()
    stale_only: bool = True
    limit: int | None = None


@dataclass(frozen=True)
class MergePreflightCommand:
    source_db_path: str
    target_db_path: str


@dataclass(frozen=True)
class MergeCorpusDatabasesCommand:
    source_db_path: str
    target_db_path: str
    snapshot_risk_confirmation_artifact_path: str | None = None
    collision_resolution_artifact_path: str | None = None
