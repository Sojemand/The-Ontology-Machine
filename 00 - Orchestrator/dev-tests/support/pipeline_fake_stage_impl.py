from __future__ import annotations

from pathlib import Path

from orchestrator.integrations import (
    ClassificationStageResult,
    CorpusLoadStageResult,
    EmbeddingStageResult,
    ExtractionStageResult,
    InterpretationStageResult,
    ModuleHealthStatus,
    NormalizationStageResult,
    ValidationStageResult,
)

from tests.pipeline_document_stage_fakes import (
    classify_document,
    extract_document_to_targets,
    interpret_document,
    validate_document,
)
from tests.pipeline_downstream_stage_fakes import generate_embeddings, healthcheck, load_document, normalize_document


class PipelineFakeStageMixin:
    def classify_document(self, source_path: Path) -> ClassificationStageResult:
        return classify_document(self, source_path)

    def extract_document_to_targets(
        self,
        source_path: Path,
        raw_output_path: Path,
        page_images_dir: Path,
        *,
        module_key: str | None = None,
        optimizer_profile: str | None = None,
        logical_source_path: str | None = None,
        runtime_policy_path: Path | None = None,
        ocr_request_dir: Path | None = None,
    ) -> ExtractionStageResult:
        return extract_document_to_targets(
            self,
            source_path,
            raw_output_path,
            page_images_dir,
            module_key=module_key,
            optimizer_profile=optimizer_profile,
            logical_source_path=logical_source_path,
            runtime_policy_path=runtime_policy_path,
            ocr_request_dir=ocr_request_dir,
        )

    def interpret_document(
        self,
        input_path: Path,
        output_path: Path,
        *,
        module_key: str | None = None,
        interpreter_profile: str | None = None,
        debug_bundle_dir: Path | None = None,
    ) -> InterpretationStageResult:
        return interpret_document(
            self,
            input_path,
            output_path,
            module_key=module_key,
            interpreter_profile=interpreter_profile,
            debug_bundle_dir=debug_bundle_dir,
        )

    def validate_document(
        self,
        structured_path: Path,
        validation_output_path: Path,
        *,
        raw_path: Path | None = None,
    ) -> ValidationStageResult:
        return validate_document(self, structured_path, validation_output_path, raw_path=raw_path)

    def normalize_document(
        self,
        structured_path: Path,
        normalized_output_path: Path,
        *,
        request_output_path: Path | None = None,
        release: dict[str, object] | None = None,
    ) -> NormalizationStageResult:
        return normalize_document(
            self,
            structured_path,
            normalized_output_path,
            request_output_path=request_output_path,
            release=release,
        )

    def load_document(
        self,
        structured_path: Path,
        validation_path: Path,
        normalized_path: Path,
        raw_path: Path | None,
        corpus_db_path: Path,
        *,
        persist_page_images_in_db: bool | None = None,
        page_images_dir: Path | None = None,
    ) -> CorpusLoadStageResult:
        return load_document(
            self,
            structured_path,
            validation_path,
            normalized_path,
            raw_path,
            corpus_db_path,
            persist_page_images_in_db=persist_page_images_in_db,
            page_images_dir=page_images_dir,
        )

    def generate_embeddings(self, corpus_db_path: Path, *, force_enable: bool = False) -> EmbeddingStageResult:
        return generate_embeddings(self, corpus_db_path, force_enable=force_enable)

    def healthcheck(
        self,
        *,
        module_keys: tuple[str, ...] | None = None,
        scope: str = "pipeline_run",
        required_dependencies_by_module: dict[str, tuple[str, ...]] | None = None,
        corpus_db_path: Path | None = None,
    ) -> list[ModuleHealthStatus]:
        return healthcheck(
            self,
            module_keys=module_keys,
            scope=scope,
            required_dependencies_by_module=required_dependencies_by_module,
            corpus_db_path=corpus_db_path,
        )
