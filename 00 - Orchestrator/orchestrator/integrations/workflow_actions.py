"""Operation methods for sibling-module contract calls."""

from __future__ import annotations

from pathlib import Path

from . import adapter, registry
from .types import (
    ClassificationStageResult,
    ExtractionStageResult,
    InterpretationStageResult,
    NormalizationStageResult,
    ValidationStageResult,
)
from .workflow_helpers import call_operation, env_overlay_for, required_runtime_settings_for, runtime_credentials_for


class SubmodulePipelineModulesActions:
    def classify_document(self, source_path: Path) -> ClassificationStageResult:
        return call_operation(
            self,
            "classify_document",
            {"source_path": str(source_path)},
            parse=adapter.parse_classification_result,
            on_error=lambda exc: ClassificationStageResult(status="error", error=str(exc)),
            log_message=f"Optimizer classify_document failed for {source_path}",
        )

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
    ) -> ExtractionStageResult:
        target_module_key = module_key or "optimizer"
        display_name = registry.module_entry(target_module_key).display_name
        payload = {
            "source_path": str(source_path),
            "raw_output_path": str(raw_output_path),
            "page_assets_dir": str(page_assets_dir),
            "logical_source_path": logical_source_path or "",
        }
        if optimizer_profile is not None:
            payload["optimizer_profile"] = str(optimizer_profile)
        if runtime_policy_path is not None:
            payload["runtime_policy_path"] = str(runtime_policy_path)
        if ocr_request_dir is not None:
            payload["ocr_request_dir"] = str(ocr_request_dir)
        env_overlay = None
        if target_module_key == "optimizer":
            if str(optimizer_profile or "").strip().lower() == "vision":
                env_overlay = env_overlay_for(self, "optimizer")
            else:
                credentials = runtime_credentials_for(self, "optimizer")
                env_overlay = credentials.env_overlay if credentials is not None and credentials.ready else None
        return call_operation(
            self,
            "extract_document",
            payload,
            parse=adapter.parse_extraction_result,
            on_error=lambda exc: ExtractionStageResult(status="error", error=str(exc)),
            log_message=f"{display_name} extract_document failed for {source_path}",
            module_key=target_module_key,
            env_overlay=env_overlay,
        )

    def interpret_document(
        self,
        input_path: Path,
        structured_output_path: Path,
        *,
        module_key: str | None = None,
        interpreter_profile: str | None = None,
        debug_bundle_dir: Path | None = None,
    ) -> InterpretationStageResult:
        target_module_key = module_key or "interpreter"
        display_name = registry.module_entry(target_module_key).display_name
        payload = _interpret_payload(
            target_module_key,
            input_path,
            structured_output_path,
            interpreter_profile=interpreter_profile,
            debug_bundle_dir=debug_bundle_dir,
        )
        if target_module_key == "interpreter":
            payload["runtime_settings"] = required_runtime_settings_for(self, target_module_key)
        return call_operation(
            self,
            "interpret_document",
            payload,
            parse=adapter.parse_interpretation_result,
            on_error=lambda exc: InterpretationStageResult(status="error", error=str(exc)),
            log_message=f"{display_name} interpret_document failed for {input_path}",
            module_key=target_module_key,
            env_overlay=env_overlay_for(self, target_module_key),
        )

    def validate_document(
        self,
        structured_path: Path,
        validation_output_path: Path,
        *,
        raw_path: Path | None = None,
    ) -> ValidationStageResult:
        payload = {
            "structured_path": str(structured_path),
            "validation_output_path": str(validation_output_path),
        }
        if raw_path is not None:
            payload["raw_path"] = str(raw_path)
        return call_operation(
            self,
            "validate_document",
            payload,
            parse=adapter.parse_validation_result,
            on_error=lambda exc: ValidationStageResult(status="ERROR", error=str(exc)),
            log_message=f"Validator call failed for {structured_path}",
        )

    def normalize_document(
        self,
        structured_path: Path,
        normalized_output_path: Path,
        *,
        request_output_path: Path | None = None,
        release: dict[str, object] | None = None,
    ) -> NormalizationStageResult:
        payload = {
            "structured_path": str(structured_path),
            "normalized_output_path": str(normalized_output_path),
            "runtime_settings": required_runtime_settings_for(self, "normalizer"),
        }
        if request_output_path is not None:
            payload["request_output_path"] = str(request_output_path)
        if release is not None:
            payload["release"] = release
        return call_operation(
            self,
            "normalize_document",
            payload,
            parse=adapter.parse_normalization_result,
            on_error=lambda exc: NormalizationStageResult(status="ERROR", error=str(exc)),
            log_message=f"Normalizer call failed for {structured_path}",
            env_overlay=env_overlay_for(self, "normalizer"),
        )


def _interpret_payload(
    target_module_key: str,
    input_path: Path,
    structured_output_path: Path,
    *,
    interpreter_profile: str | None = None,
    debug_bundle_dir: Path | None = None,
) -> dict[str, str]:
    del target_module_key
    payload = {
        "request_path": str(input_path),
        "structured_output_path": str(structured_output_path),
    }
    if debug_bundle_dir is not None:
        payload["debug_bundle_dir"] = str(debug_bundle_dir)
    if interpreter_profile is not None:
        payload["interpreter_profile"] = str(interpreter_profile)
    return payload
