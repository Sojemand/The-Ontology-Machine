"""Downstream and administrative integration operations."""

from __future__ import annotations

from pathlib import Path

from . import adapter
from .types import CorpusLoadStageResult, EmbeddingStageResult, ModuleHealthStatus, ReleaseActivationStageResult
from .workflow_helpers import call_operation, healthcheck_statuses, required_runtime_settings_for, runtime_credentials_for


class SubmodulePipelineModulesDownstreamActions:
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
    ) -> CorpusLoadStageResult:
        raw_path: Path | None
        if corpus_db_path is None:
            raw_path = None
            corpus_db_path = raw_path_or_corpus_db_path
        else:
            raw_path = raw_path_or_corpus_db_path
        if corpus_db_path is None:
            return CorpusLoadStageResult(status="error", reason="corpus_db_path is missing.")
        runtime_credentials = runtime_credentials_for(self, "corpus_builder", "load_document")
        return call_operation(
            self,
            "load_document",
            {
                "structured_path": str(structured_path),
                "validation_path": str(validation_path),
                "normalized_path": str(normalized_path),
                **({"raw_path": str(raw_path)} if raw_path is not None else {}),
                "corpus_db_path": str(corpus_db_path),
                **({"persist_page_images_in_db": persist_page_images_in_db} if persist_page_images_in_db is not None else {}),
                **({"page_images_dir": str(page_images_dir)} if page_images_dir is not None else {}),
            },
            parse=adapter.parse_corpus_load_result,
            on_error=lambda exc: CorpusLoadStageResult(status="error", reason=str(exc)),
            log_message=f"Corpus load failed for {structured_path}",
            module_key="corpus_builder",
            env_overlay=runtime_credentials.env_overlay if runtime_credentials is not None and runtime_credentials.ready else None,
        )

    def activate_semantic_release(
        self,
        release_path: Path,
        corpus_db_path: Path,
        confirmation_artifact_path: Path | None = None,
    ) -> ReleaseActivationStageResult:
        return call_operation(
            self,
            "activate_semantic_release",
            {
                "release_path": str(release_path),
                "corpus_db_path": str(corpus_db_path),
                **(
                    {"confirmation_artifact_path": str(confirmation_artifact_path)}
                    if confirmation_artifact_path is not None
                    else {}
                ),
            },
            parse=adapter.parse_release_activation_result,
            on_error=lambda exc: ReleaseActivationStageResult(status="error", reason=str(exc)),
            log_message=f"Semantic release activation failed for {release_path}",
        )

    def generate_embeddings(self, corpus_db_path: Path) -> EmbeddingStageResult:
        runtime_credentials = runtime_credentials_for(self, "corpus_builder", "generate_embeddings")
        if runtime_credentials is not None and not runtime_credentials.ready and runtime_credentials.warning_only:
            return EmbeddingStageResult(status="disabled", reason=runtime_credentials.message)
        return call_operation(
            self,
            "generate_embeddings",
            {
                "corpus_db_path": str(corpus_db_path),
                "runtime_settings": required_runtime_settings_for(self, "corpus_builder", "generate_embeddings"),
            },
            parse=adapter.parse_embedding_result,
            on_error=lambda exc: EmbeddingStageResult(status="error", reason=str(exc)),
            log_message=f"Embedding generation failed for {corpus_db_path}",
            module_key="corpus_builder",
            env_overlay=runtime_credentials.env_overlay if runtime_credentials is not None else None,
        )

    def healthcheck(
        self,
        *,
        module_keys: tuple[str, ...] | None = None,
        scope: str = "pipeline_run",
        required_dependencies_by_module: dict[str, tuple[str, ...]] | None = None,
        corpus_db_path: Path | None = None,
    ) -> list[ModuleHealthStatus]:
        return healthcheck_statuses(
            self,
            module_keys=module_keys,
            scope=scope,
            required_dependencies_by_module=required_dependencies_by_module,
            corpus_db_path=corpus_db_path,
        )

    def close(self) -> None:
        return None

    def _runtime_settings_for(self, module_key: str, operation: str = "") -> dict[str, object] | None:
        return self._runtime_settings.runtime_settings_for(module_key, operation)
