"""Visible request enrichment stage between optimizer and interpreter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import debug, document_types, request_enrichment
from .page_stage_types import PageStageResult


def run_request_enrichment_page(
    engine: Any,
    record: Any,
    ctx: Any,
    paths: Any,
    raw_path: Path,
    *,
    page_index: int,
    page_total: int,
) -> PageStageResult:
    stage_name = request_enrichment.REQUEST_ENRICHMENT_STAGE_NAME
    runtime_semantics = getattr(ctx, "runtime_semantics", None)
    projection_catalog = getattr(runtime_semantics, "projection_catalog", None)
    if not isinstance(projection_catalog, dict):
        return PageStageResult.failure(
            "Request Enrichment failed: projection_catalog is missing in the run-scoped runtime bundle."
        )
    detail = f"{record.route_family} | {_page_detail(raw_path, page_index, page_total)}"
    debug.set_stage(
        engine,
        stage_name,
        "Processing...",
        detail,
        progress_current=page_index,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    try:
        request_path = _target_request_path(paths, raw_path, page_total=page_total)
        request_enrichment.build_working_request(
            engine._modules,
            interpreter_profile=getattr(record, "interpreter_profile", "") or "vision",
            raw_path=raw_path,
            request_path=request_path,
            working_source_path=paths.working_source_path,
            working_page_paths=tuple(Path(path) for path in record.artifacts.optimizer_page_image_paths),
            projection_catalog=projection_catalog,
        )
    except Exception as exc:
        return PageStageResult.failure(f"Request Enrichment failed: {exc}")
    debug.set_stage(
        engine,
        stage_name,
        "Done",
        _page_detail(request_path, page_index, page_total),
        progress_current=page_index + 1,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    return PageStageResult.success(request_path)


def _target_request_path(paths: Any, raw_path: Path, *, page_total: int) -> Path:
    if page_total <= 1:
        return paths.working_request_path
    return document_types.page_request_path(paths, raw_path)


def _page_detail(raw_path: Path, page_index: int, page_total: int) -> str:
    if page_total <= 1:
        return raw_path.name
    return f"Page {page_index + 1}/{page_total} | {raw_path.name}"
