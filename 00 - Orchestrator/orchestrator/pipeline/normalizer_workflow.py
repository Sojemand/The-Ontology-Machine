"""Page-scoped Normalizer stage workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..integrations import stage_name_for_module
from . import debug, document_types, policy, validation
from .page_stage_types import PageStageResult


def run_normalizer_page(
    engine: Any,
    record: Any,
    ctx: Any,
    paths: Any,
    structured_path: Path,
    *,
    request_output_path: Path | None = None,
    page_index: int,
    page_total: int,
) -> PageStageResult:
    stage_name = stage_name_for_module("normalizer")
    debug.check_cancelled(engine)
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
    runtime_release = getattr(getattr(ctx, "runtime_semantics", None), "release", None)
    target_normalized_path = _target_normalized_path(paths, structured_path, request_total=page_total)
    normalization = engine._modules.normalize_document(
        structured_path,
        target_normalized_path,
        request_output_path=request_output_path,
        release=runtime_release if isinstance(runtime_release, dict) else None,
    )
    emitted_request_path = request_output_path if request_output_path is not None and request_output_path.exists() else None
    failure_reason = policy.normalizer_failure_reason(normalization)
    normalized_path, normalized_error = validation.validated_existing_file_path(
        engine,
        normalization.output_path,
        allowed_roots=ctx.managed_roots,
        action="Normalizer-Output",
        noun="Normalizer output",
        missing_message="" if failure_reason else "Normalizer did not provide an output path.",
    )
    if normalized_path is not None and not normalized_error:
        expected_path = validation.resolved_path(target_normalized_path)
        actual_path = validation.resolved_path(normalized_path)
        if actual_path != expected_path:
            normalized_error = f"Normalizer output path deviates from the requested path: {normalized_path}"
    if failure_reason or normalized_error or normalized_path is None:
        return PageStageResult.failure(
            failure_reason or normalized_error or "Normalizer did not provide an output path.",
            request_path=emitted_request_path,
        )
    stage_status = "Review" if normalization.needs_review else "Done"
    stage_detail = normalization.review_reason or normalization.message or normalized_path.name
    debug.set_stage(
        engine,
        stage_name,
        stage_status,
        stage_detail,
        progress_current=page_index + 1,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    return PageStageResult.success(
        normalized_path,
        request_path=emitted_request_path,
        needs_review=bool(normalization.needs_review),
        review_stage="normalizer",
        review_reason=normalization.review_reason or normalization.message or "Normalizer reported needs_review.",
    )


def _target_normalized_path(paths: Any, structured_path: Path, *, request_total: int) -> Path:
    if request_total == 1:
        return paths.working_normalized_path
    return document_types.page_normalized_path(paths, structured_path)


def _page_detail(path: Path, page_index: int, page_total: int) -> str:
    if page_total <= 1:
        return path.name
    return f"Page {page_index + 1}/{page_total} | {path.name}"
