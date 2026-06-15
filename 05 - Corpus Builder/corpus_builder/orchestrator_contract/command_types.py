"""Command dataclasses for standard contract actions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models.types import EmbeddingRuntimeSettings


@dataclass(frozen=True)
class LoadDocumentCommand:
    corpus_db_path: str
    normalized_path: str
    structured_path: str
    validation_path: str
    raw_path: str | None = None
    persist_page_images_in_db: bool | None = None
    page_images_dir: str | None = None


@dataclass(frozen=True)
class ActivateSemanticReleaseCommand:
    release_path: str
    corpus_db_path: str | None = None
    confirmation_artifact_path: str | None = None
    write_global_mirrors: bool = True


@dataclass(frozen=True)
class ActivateCorpusContextCommand:
    corpus_db_path: str


@dataclass(frozen=True)
class CreateEmptyCorpusDbCommand:
    corpus_db_path: str
    activate_context: bool = False


@dataclass(frozen=True)
class ResetActiveCorpusDbCommand:
    confirmation_artifact_path: str
    corpus_db_path: str | None = None


@dataclass(frozen=True)
class CreateAndActivateNewCorpusDbCommand:
    release_path: str
    confirmation_artifact_path: str


@dataclass(frozen=True)
class ActivationPreflightCommand:
    release_path: str
    corpus_db_path: str | None = None


@dataclass(frozen=True)
class GenerateEmbeddingsCommand:
    corpus_db_path: str
    runtime_settings: EmbeddingRuntimeSettings


@dataclass(frozen=True)
class HealthcheckCommand:
    runtime_settings: EmbeddingRuntimeSettings
    scope: str | None = None
    corpus_db_path: str | None = None


@dataclass(frozen=True)
class ScanDebugInputCommand:
    mode: str
    session_root: Path
    input_root: Path


@dataclass(frozen=True)
class DebugRunCommand:
    mode: str
    session_root: Path
    output_root: Path
    input_root: Path | None = None
    source_path: Path | None = None
    persist_page_images_in_db: bool = False


@dataclass(frozen=True)
class ValidateArtifactTreeCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReadDatabaseAnalysisEvidenceCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class InspectLatestPipelineBatchCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class ExtractSampleFilesForReingestCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class RestorePipelineBatchOriginalsCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class CleanupPipelineBatchMaterializationCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReingestPipelineBatchCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class MultiSourceMergePreflightCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class MultiSourceMergeDatabasesCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class WriteMergeReconciliationManifestCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class BackfillSqlFromMergeArtifactsCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class BasicRelationMiningCommand:
    corpus_db_path: str | None = None
    dry_run: bool = False
