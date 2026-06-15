"""Contract response parsing for sibling-module integrations."""

from __future__ import annotations

import subprocess
from typing import Any

from ..bootstrap import ModuleRuntimeSpec
from .policy import coerce_contract_bool, coerce_contract_int, coerce_contract_str, coerce_contract_str_list
from .types import (
    ClassificationStageResult,
    CorpusLoadStageResult,
    EmbeddingStageResult,
    ExternalDependencyStatus,
    ExtractionStageResult,
    InterpretationStageResult,
    ModuleHealthStatus,
    NormalizationStageResult,
    ReleaseActivationStageResult,
    ValidationStageResult,
)


def response_error(data: dict[str, Any]) -> str:
    return str(data.get("error") or data.get("reason") or data.get("message") or "").strip()


def contract_failure_text(display_name: str, completed: subprocess.CompletedProcess, data: dict[str, Any]) -> str:
    message = response_error(data)
    stderr = str(completed.stderr or "").strip()
    stdout = str(completed.stdout or "").strip()
    details = message or stderr or stdout or f"Exit code {completed.returncode}"
    return f"{display_name} failed: {details}"


def parse_extraction_result(data: dict[str, Any]) -> ExtractionStageResult:
    return ExtractionStageResult(
        status=coerce_contract_str(data.get("status", "error"), "error"),
        content_hash=coerce_contract_str(data.get("content_hash", "")),
        ingest_id=coerce_contract_str(data.get("ingest_id", "")),
        document_raw_path=coerce_contract_str(data.get("document_raw_path", "")),
        page_raw_paths=coerce_contract_str_list(data.get("page_raw_paths", [])),
        page_asset_paths=coerce_contract_str_list(data.get("page_asset_paths", [])),
        ocr_request_paths=coerce_contract_str_list(data.get("ocr_request_paths", [])),
        error=response_error(data),
    )


def parse_classification_result(data: dict[str, Any]) -> ClassificationStageResult:
    return ClassificationStageResult(
        status=coerce_contract_str(data.get("status", "error"), "error"),
        classification=coerce_contract_str(data.get("classification", "")),
        reason=coerce_contract_str(data.get("reason", "")),
        error=response_error(data),
    )


def parse_interpretation_result(data: dict[str, Any]) -> InterpretationStageResult:
    return InterpretationStageResult(
        status=coerce_contract_str(data.get("status", "error"), "error"),
        structured_path=coerce_contract_str(data.get("structured_path", "")),
        debug_bundle_path=coerce_contract_str(data.get("debug_bundle_path", "")),
        needs_review=coerce_contract_bool(data.get("needs_review", False), False),
        review_reason=coerce_contract_str(data.get("review_reason", "")),
        error=response_error(data),
    )


def parse_validation_result(data: dict[str, Any]) -> ValidationStageResult:
    return ValidationStageResult(
        status=coerce_contract_str(data.get("status", "ERROR"), "ERROR"),
        report_path=coerce_contract_str(data.get("report_path", "")),
        needs_review=coerce_contract_bool(data.get("needs_review", False), False),
        detail=coerce_contract_str(data.get("detail", "")),
        error=response_error(data),
    )


def parse_normalization_result(data: dict[str, Any]) -> NormalizationStageResult:
    return NormalizationStageResult(
        status=coerce_contract_str(data.get("status", "ERROR"), "ERROR"),
        output_path=coerce_contract_str(data.get("output_path", "")),
        request_path=coerce_contract_str(data.get("request_path", "")),
        needs_review=coerce_contract_bool(data.get("needs_review", False), False),
        message=coerce_contract_str(data.get("message", "")),
        review_reason=coerce_contract_str(data.get("review_reason", "")),
        error=response_error(data),
    )


def parse_corpus_load_result(data: dict[str, Any]) -> CorpusLoadStageResult:
    return CorpusLoadStageResult(
        status=coerce_contract_str(data.get("status", "error"), "error"),
        reason=coerce_contract_str(data.get("reason", "")),
    )


def parse_release_activation_result(data: dict[str, Any]) -> ReleaseActivationStageResult:
    return ReleaseActivationStageResult(
        status=coerce_contract_str(data.get("status", "error"), "error"),
        reason=coerce_contract_str(data.get("reason", "")),
        release_id=coerce_contract_str(data.get("release_id", "")),
        release_version=coerce_contract_str(data.get("release_version", "")),
        active_snapshot_id=coerce_contract_str(data.get("active_snapshot_id", "")),
        stale_documents=coerce_contract_int(data.get("stale_documents", 0), 0),
        backfill_started=coerce_contract_bool(data.get("backfill_started", False), False),
        backfill_processed_count=coerce_contract_int(data.get("backfill_processed_count", 0), 0),
    )


def parse_embedding_result(data: dict[str, Any]) -> EmbeddingStageResult:
    return EmbeddingStageResult(
        status=coerce_contract_str(data.get("status", "error"), "error"),
        count=coerce_contract_int(data.get("count", 0), 0),
        reason=coerce_contract_str(data.get("reason", "")),
    )


def parse_health_status(spec: ModuleRuntimeSpec, data: dict[str, Any]) -> ModuleHealthStatus:
    dependencies = parse_dependency_statuses(data)
    healthy = (
        coerce_contract_bool(data.get("healthy"), False)
        if "healthy" in data
        else coerce_contract_str(data.get("status", ""), "").strip().lower() == "ok"
    )
    if any(dependency.required and not dependency.healthy for dependency in dependencies):
        healthy = False
    return ModuleHealthStatus(
        key=spec.key,
        display_name=spec.display_name,
        healthy=healthy,
        message=response_error(data),
        dependencies=dependencies,
    )


def parse_dependency_statuses(data: dict[str, Any]) -> list[ExternalDependencyStatus]:
    raw_dependencies = data.get("dependencies", [])
    if not isinstance(raw_dependencies, list):
        return []
    results: list[ExternalDependencyStatus] = []
    for item in raw_dependencies:
        if not isinstance(item, dict):
            continue
        name = coerce_contract_str(item.get("name", "")).strip()
        if not name:
            continue
        results.append(
            ExternalDependencyStatus(
                name=name,
                kind=coerce_contract_str(item.get("kind", "service"), "service").strip() or "service",
                required=coerce_contract_bool(item.get("required", True), True),
                healthy=dependency_is_healthy(item),
                detail=coerce_contract_str(item.get("detail", "")).strip(),
            )
        )
    return results


def dependency_is_healthy(item: dict[str, Any]) -> bool:
    if "healthy" in item:
        return coerce_contract_bool(item.get("healthy"), False)
    status = coerce_contract_str(item.get("status", ""), "").strip().lower()
    return status in {"ok", "healthy", "pass", "passed", "available"}
