"""Page-scoped error-case routing."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..integrations import module_entry, stage_name_for_module
from ..models import ArtifactPaths
from . import bundle_page_manifest, bundle_repository, debug


def route_page_to_error(
    engine: Any,
    page: Any,
    ctx: Any,
    *,
    stage: str,
    reason: str,
) -> None:
    record = page.record
    module_name = _module_name_for_failure(record, stage)
    error_bundle = bundle_repository.bundle_dir(ctx.ui_state, record, stage=stage, module_name=module_name)
    page_record = _page_error_record(record, page)
    frozen = bundle_repository.freeze_bundle_artifacts(
        engine,
        page_record,
        error_bundle,
        allowed_roots=ctx.managed_roots,
        run_log_path=debug.active_document_log_path(engine) or ctx.run_log_path,
        source_path=None,
        page_suffix=_page_suffix(page.page_index, page.page_total),
    )
    page_record.status = "error"
    page_record.final_disposition = "error"
    page_record.current_location = "page_error_bundle"
    page_record.last_stage = stage
    page_record.last_error = reason
    page_record.artifacts.optimizer_raw_paths = list(frozen.optimizer_raw_paths)
    page_record.artifacts.optimizer_page_image_paths = list(frozen.optimizer_page_image_paths)
    page_record.artifacts.optimizer_ocr_request_paths = list(frozen.optimizer_ocr_request_paths)
    page_record.artifacts.optimizer_ocr_request_path = frozen.optimizer_ocr_request_path
    page_record.artifacts.interpreter_request_paths = list(frozen.interpreter_request_paths)
    page_record.artifacts.interpreter_request_path = frozen.interpreter_request_path
    page_record.artifacts.interpreter_debug_bundle_path = frozen.interpreter_debug_bundle_path
    page_record.artifacts.structured_paths = list(frozen.structured_paths)
    page_record.artifacts.structured_path = frozen.structured_path
    page_record.artifacts.validation_report_paths = list(frozen.validation_report_paths)
    page_record.artifacts.validation_report_path = frozen.validation_report_path
    page_record.artifacts.normalized_paths = list(frozen.normalized_paths)
    page_record.artifacts.normalized_path = frozen.normalized_path
    page_record.artifacts.normalizer_request_paths = list(frozen.normalizer_request_paths)
    page_record.artifacts.normalizer_request_path = frozen.normalizer_request_path
    page_record.artifacts.bundle_dir = str(error_bundle)
    bundle_page_manifest.write_page_bundle_manifest(
        engine,
        page_record,
        error_bundle,
        stage=stage,
        reason=reason,
        disposition="page_error",
        module_name=module_name,
        page_index=page.page_index,
        page_total=page.page_total,
    )
    debug.append_log(
        engine,
        f"[PAGE-ERROR] {record.relative_path}: Page {page.page_number}/{page.page_total} -> {stage}: {reason}",
    )


def _page_error_record(record: Any, page: Any) -> Any:
    page_record = deepcopy(record)
    page_image_paths = list(getattr(record.artifacts, "optimizer_page_image_paths", []) or [])
    page_image_path = page_image_paths[page.page_index] if page.page_index < len(page_image_paths) else ""
    page_record.artifacts = ArtifactPaths(
        optimizer_raw_paths=[str(page.raw_path)] if page.raw_path else [],
        optimizer_page_image_paths=[str(page_image_path)] if str(page_image_path).strip() else [],
        optimizer_ocr_request_paths=list(getattr(record.artifacts, "optimizer_ocr_request_paths", []) or []),
        optimizer_ocr_request_path=str(getattr(record.artifacts, "optimizer_ocr_request_path", "") or ""),
        interpreter_request_paths=[str(page.request_path)] if page.request_path else [],
        interpreter_request_path=str(page.request_path) if page.request_path else "",
        interpreter_debug_bundle_path=str(
            page.interpreter_debug_bundle_path or getattr(record.artifacts, "interpreter_debug_bundle_path", "") or ""
        ),
        structured_paths=[str(page.structured_path)] if page.structured_path else [],
        structured_path=str(page.structured_path) if page.structured_path else "",
        validation_report_paths=[str(page.validation_path)] if page.validation_path else [],
        validation_report_path=str(page.validation_path) if page.validation_path else "",
        normalized_paths=[str(page.normalized_path)] if page.normalized_path else [],
        normalized_path=str(page.normalized_path) if page.normalized_path else "",
        normalizer_request_paths=[str(page.normalizer_request_path)] if page.normalizer_request_path else [],
        normalizer_request_path=str(page.normalizer_request_path) if page.normalizer_request_path else "",
    )
    return page_record


def _page_suffix(page_index: int, page_total: int) -> str:
    return f".p{page_index + 1:03d}.of{max(page_total, 1):03d}"


def _module_name_for_failure(record: Any, stage: str) -> str:
    if stage == stage_name_for_module("validator"):
        return module_entry("validator").display_name
    if stage == stage_name_for_module("normalizer"):
        return module_entry("normalizer").display_name
    if stage == stage_name_for_module("corpus_builder"):
        return module_entry("corpus_builder").display_name
    if stage == "Interpreter" and record.interpreter_module_key:
        return module_entry(record.interpreter_module_key).display_name
    return str(stage or "Unbekannt").strip() or "Unbekannt"
