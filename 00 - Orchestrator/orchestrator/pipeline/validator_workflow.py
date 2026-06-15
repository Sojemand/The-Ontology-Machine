"""Validator stage workflow for pipeline records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..integrations import stage_name_for_module
from . import debug, document_types, validation
from .page_stage_types import PageStageResult


def run_validator_page(
    engine: Any,
    record: Any,
    ctx: Any,
    paths: Any,
    structured_path: Path,
    raw_path: Path,
    *,
    page_index: int,
    page_total: int,
) -> PageStageResult:
    stage_name = stage_name_for_module("validator")
    debug.set_stage(
        engine,
        stage_name,
        "Processing...",
        _page_detail(structured_path, page_index, page_total),
        progress_current=page_index,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    validation_output_path = _target_page_validation_path(
        paths,
        structured_path,
        files_profile=getattr(record, "interpreter_profile", "") == "file",
        page_total=page_total,
    )
    raw_evidence_path = None
    if getattr(record, "interpreter_profile", "") == "file":
        raw_evidence_path, raw_error = validation.validated_existing_file_path(
            engine,
            str(raw_path),
            allowed_roots=ctx.managed_roots,
            action="Validator-Raw-Evidence",
            noun="Optimizer raw output",
            missing_message="Interpreter path without raw evidence: optimizer did not provide raw output.",
        )
        if raw_error:
            return PageStageResult.failure(raw_error)
    try:
        validation_result = engine._modules.validate_document(
            structured_path,
            validation_output_path,
            raw_path=raw_evidence_path,
        )
    except Exception as exc:
        return PageStageResult.failure(f"Validator could not be executed: {exc}")
    if validation_result.status == "ERROR":
        return PageStageResult.failure(validation_result.error or "Unknown error")
    report_path, report_error = validation.validated_existing_file_path(
        engine,
        validation_result.report_path,
        allowed_roots=ctx.managed_roots,
        action="Validator-Report",
        noun="Validator report",
        missing_message="Validator did not provide a report path.",
    )
    if report_error:
        return PageStageResult.failure(report_error)
    if report_path.resolve() != validation_output_path.resolve():
        return PageStageResult.failure(f"Validator report deviates from the planned target path: {report_path}", path=report_path)
    validation_status = str(validation_result.status or "").strip().upper()
    debug.set_stage(
        engine,
        stage_name,
        validation_status,
        validation_result.detail,
        progress_current=page_index + 1,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    if validation_status == "FAIL":
        return PageStageResult.failure(
            validation_result.detail or "Validator FAIL",
            path=report_path,
            retry_from="interpreter",
            status=validation_status,
        )
    if validation_status not in {"PASS", "WARN"}:
        return PageStageResult.failure(
            validation_result.detail or f"Validator returned unknown status: {validation_result.status!r}",
            path=report_path,
            status=validation_status,
        )
    review_reason = validation_result.detail or f"Validator {validation_result.status or 'WARN'}"
    return PageStageResult.success(
        report_path,
        status=validation_status,
        needs_review=bool(validation_result.needs_review),
        review_stage="validator",
        review_reason=review_reason if validation_result.needs_review else "",
    )

def _target_page_validation_path(paths: Any, structured_path: Path, *, files_profile: bool, page_total: int) -> Path:
    if page_total <= 1:
        return paths.working_validation_path
    return document_types.page_validation_path(paths, structured_path, files_profile=files_profile)


def _page_detail(path: Path, page_index: int, page_total: int) -> str:
    if page_total <= 1:
        return path.name
    return f"Page {page_index + 1}/{page_total} | {path.name}"
