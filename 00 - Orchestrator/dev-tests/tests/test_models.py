from __future__ import annotations

import orchestrator.models as models
from orchestrator.models import ArtifactPaths, DocumentRecord, PipelineSnapshot, PipelineState, STAGE_NAMES


def test_public_surface_reexports_expected_symbols() -> None:
    assert models.UiState.__name__ == "UiState"
    assert models.DocumentRecord is DocumentRecord
    assert models.PipelineState is PipelineState
    assert models.PipelineSnapshot is PipelineSnapshot
    assert models.RunSummary.__name__ == "RunSummary"
    assert models.ResetSummary.__name__ == "ResetSummary"
    assert models.__all__ == [
        "ArtifactPaths",
        "DocumentRecord",
        "EmbeddingRuntimeSettings",
        "LlmRuntimeSettings",
        "OptimizerOcrRuntimeSettings",
        "PipelineLogResetSummary",
        "PipelineSnapshot",
        "PipelineState",
        "ProviderEndpointSettings",
        "ResetSummary",
        "RuntimeSettingsState",
        "RunSummary",
        "STAGE_NAMES",
        "StageSnapshot",
        "UiState",
        "default_corpus_builder_embeddings_runtime_settings",
        "default_embeddings_provider_settings",
        "default_interpreter_runtime_settings",
        "default_llm_shared_provider_settings",
        "default_normalizer_runtime_settings",
        "default_optimizer_ocr_provider_settings",
        "default_optimizer_ocr_runtime_settings",
        "normalize_provider_id",
        "provider_definition",
        "provider_display_names",
        "provider_id_for_display_name",
        "provider_ids_for_target",
        "provider_note",
        "utc_now_iso",
    ]


def test_pipeline_state_roundtrip_preserves_nested_document_artifacts() -> None:
    record = DocumentRecord(
        content_hash="sha256:test",
        file_name="doc.pdf",
        relative_path="nested/doc.pdf",
        source_path="C:/input/nested/doc.pdf",
        route_family="Documents",
        optimizer_module_key="optimizer",
        interpreter_module_key="interpreter",
        intake_reason="Born-digital PDF detected.",
        artifacts=ArtifactPaths(
            optimizer_raw_paths=["raw/doc.raw.json"],
            optimizer_page_image_paths=["page_images/doc/page_001.jpg"],
            interpreter_request_path="requests/doc.pdf/interpreter.request.json",
            interpreter_debug_bundle_path="runtime/doc/interpreter_debug/doc.debug.json",
            structured_path="structured/doc.structured.json",
            bundle_dir="errors/Documents/Validator/doc.bundle",
        ),
    )

    loaded = PipelineState.from_dict(PipelineState(documents={record.content_hash: record}).to_dict())

    restored = loaded.documents["sha256:test"]
    assert restored.file_name == "doc.pdf"
    assert restored.relative_path == "nested/doc.pdf"
    assert restored.route_family == "Documents"
    assert restored.optimizer_module_key == "optimizer"
    assert restored.interpreter_module_key == "interpreter"
    assert restored.intake_reason == "Born-digital PDF detected."
    assert restored.artifacts.optimizer_raw_paths == ["raw/doc.raw.json"]
    assert restored.artifacts.optimizer_page_image_paths == ["page_images/doc/page_001.jpg"]
    assert restored.artifacts.interpreter_request_path == "requests/doc.pdf/interpreter.request.json"
    assert restored.artifacts.interpreter_debug_bundle_path == "runtime/doc/interpreter_debug/doc.debug.json"
    assert restored.artifacts.structured_path == "structured/doc.structured.json"
    assert restored.artifacts.bundle_dir == "errors/Documents/Validator/doc.bundle"


def test_pipeline_snapshot_defaults_cover_all_stages_with_independent_maps() -> None:
    first = PipelineSnapshot()
    second = PipelineSnapshot()

    assert tuple(first.stage_statuses) == STAGE_NAMES
    assert all(
        stage.status == "Ready"
        and stage.detail == ""
        and stage.progress_current == 0
        and stage.progress_total == 0
        and stage.progress_label == ""
        for stage in first.stage_statuses.values()
    )

    first.stage_statuses["Interpreter"].status = "Review"
    assert second.stage_statuses["Interpreter"].status == "Ready"


def test_clear_normal_outputs_resets_only_normal_processing_paths() -> None:
    artifacts = ArtifactPaths(
        optimizer_raw_paths=["raw/a.json"],
        optimizer_page_image_paths=["pages/a.png"],
        interpreter_request_path="requests/a/interpreter.request.json",
        interpreter_debug_bundle_path="runtime/a/interpreter_debug/a.debug.json",
        structured_path="structured/a.json",
        normalized_path="normalized/a.json",
        validation_report_path="validation/a.json",
        bundle_dir="errors/Documents/Normalizer/a.bundle",
        bundle_manifest_path="errors/Documents/Normalizer/a.bundle/manifest.json",
    )

    artifacts.clear_normal_outputs()

    assert artifacts.optimizer_raw_paths == []
    assert artifacts.optimizer_page_image_paths == []
    assert artifacts.interpreter_request_path == ""
    assert artifacts.interpreter_debug_bundle_path == ""
    assert artifacts.structured_path == ""
    assert artifacts.normalized_path == ""
    assert artifacts.validation_report_path == ""
    assert artifacts.bundle_dir == "errors/Documents/Normalizer/a.bundle"
    assert artifacts.bundle_manifest_path == "errors/Documents/Normalizer/a.bundle/manifest.json"

