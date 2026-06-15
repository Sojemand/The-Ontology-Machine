"""Public types for the orchestrator integration surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

RequiredDependenciesByModule = dict[str, tuple[str, ...]]


@dataclass
class ExtractionStageResult:
    status: str = "error"
    content_hash: str = ""
    ingest_id: str = ""
    document_raw_path: str = ""
    page_raw_paths: list[str] = field(default_factory=list)
    page_asset_paths: list[str] = field(default_factory=list)
    ocr_request_paths: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class ClassificationStageResult:
    status: str = "error"
    classification: str = ""
    reason: str = ""
    error: str = ""


@dataclass
class InterpretationStageResult:
    status: str = "error"
    structured_path: str = ""
    debug_bundle_path: str = ""
    needs_review: bool = False
    review_reason: str = ""
    error: str = ""


@dataclass
class ValidationStageResult:
    status: str = "ERROR"
    report_path: str = ""
    needs_review: bool = False
    detail: str = ""
    error: str = ""


@dataclass
class NormalizationStageResult:
    status: str = "ERROR"
    output_path: str = ""
    request_path: str = ""
    needs_review: bool = False
    message: str = ""
    review_reason: str = ""
    error: str = ""


@dataclass
class CorpusLoadStageResult:
    status: str = "error"
    reason: str = ""


@dataclass
class ReleaseActivationStageResult:
    status: str = "error"
    reason: str = ""
    release_id: str = ""
    release_version: str = ""
    active_snapshot_id: str = ""
    stale_documents: int = 0
    backfill_started: bool = False
    backfill_processed_count: int = 0


@dataclass
class EmbeddingStageResult:
    status: str = "error"
    count: int = 0
    reason: str = ""


@dataclass
class ExternalDependencyStatus:
    name: str
    kind: str = "service"
    required: bool = True
    healthy: bool = True
    detail: str = ""


@dataclass
class ModuleHealthStatus:
    key: str
    display_name: str
    healthy: bool = True
    message: str = ""
    dependencies: list[ExternalDependencyStatus] = field(default_factory=list)

    def blocking_issues(self) -> list[str]:
        issues = [
            dependency.detail or dependency.name
            for dependency in self.dependencies
            if dependency.required and not dependency.healthy
        ]
        if issues:
            return issues
        if not self.healthy:
            return [self.message or f"{self.display_name} ist nicht bereit."]
        return []

    def optional_issues(self) -> list[str]:
        return [
            dependency.detail or dependency.name
            for dependency in self.dependencies
            if not dependency.required and not dependency.healthy
        ]


class PipelineModules(Protocol):
    def classify_document(self, source_path: Path) -> ClassificationStageResult: ...

    def extract_document_to_targets(
        self,
        source_path: Path,
        raw_output_path: Path,
        page_assets_dir: Path,
        *,
        module_key: str | None = None,
        optimizer_profile: str | None = None,
        logical_source_path: str | None = None,
        runtime_policy_path: Path | None = None,
        ocr_request_dir: Path | None = None,
    ) -> ExtractionStageResult: ...

    def interpret_document(
        self,
        input_path: Path,
        structured_output_path: Path,
        *,
        module_key: str | None = None,
        interpreter_profile: str | None = None,
        debug_bundle_dir: Path | None = None,
    ) -> InterpretationStageResult: ...

    def validate_document(
        self,
        structured_path: Path,
        validation_output_path: Path,
        *,
        raw_path: Path | None = None,
    ) -> ValidationStageResult: ...

    def normalize_document(
        self,
        structured_path: Path,
        normalized_output_path: Path,
        *,
        request_output_path: Path | None = None,
        release: dict[str, Any] | None = None,
    ) -> NormalizationStageResult: ...

    def load_document(
        self,
        structured_path: Path,
        validation_path: Path,
        normalized_path: Path,
        raw_path_or_corpus_db_path: Path | None,
        corpus_db_path: Path | None = None,
        *,
        persist_page_images_in_db: bool | None = None,
        page_images_dir: Path | None = None,
    ) -> CorpusLoadStageResult: ...

    def activate_semantic_release(
        self,
        release_path: Path,
        corpus_db_path: Path,
        confirmation_artifact_path: Path | None = None,
    ) -> ReleaseActivationStageResult: ...

    def generate_embeddings(self, corpus_db_path: Path) -> EmbeddingStageResult: ...

    def healthcheck(
        self,
        *,
        module_keys: tuple[str, ...] | None = None,
        scope: str = "pipeline_run",
        required_dependencies_by_module: RequiredDependenciesByModule | None = None,
        corpus_db_path: Path | None = None,
    ) -> list[ModuleHealthStatus]: ...

    def close(self) -> None: ...
class ModuleContractError(RuntimeError):
    """Raised when a sibling module contract call fails."""
