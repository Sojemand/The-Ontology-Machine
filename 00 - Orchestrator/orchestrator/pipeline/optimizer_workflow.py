"""Optimizer stage workflow for pipeline records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..integrations import module_entry, stage_name_for_module
from . import debug, error_workflow, intake_workflow, optimizer_support, storage_repository


def run_optimizer(engine: Any, record: Any, ctx: Any, paths: Any) -> list[Path] | None:
    module_key = record.optimizer_module_key or "optimizer"
    display_name = module_entry(module_key).display_name
    stage_name = stage_name_for_module(module_key)
    debug.set_stage(engine, stage_name, "Processing...", intake_workflow.describe_route(record))
    debug.emit_snapshot(engine)
    raw_dest = optimizer_support.requested_raw_output_path(engine, record, paths)
    page_dir = optimizer_support.requested_page_assets_dir(engine, record, paths)
    ocr_request_dir = optimizer_support.requested_ocr_request_dir(paths)
    logical_source_path = optimizer_support.logical_source_path(engine, record)
    runtime_policy_path = None
    if getattr(record, "optimizer_profile", "") == "vision" and getattr(ctx, "runtime_semantics", None) is not None:
        runtime_policy_path = ctx.runtime_semantics.runtime_policy_path
    extraction = engine._modules.extract_document_to_targets(
        paths.working_source_path,
        raw_dest,
        page_dir,
        module_key=module_key,
        optimizer_profile=getattr(record, "optimizer_profile", "") or "vision",
        logical_source_path=logical_source_path,
        runtime_policy_path=runtime_policy_path,
        ocr_request_dir=ocr_request_dir,
    )
    if extraction.status != "ok":
        error_workflow.handle_failure(engine, record, ctx, stage_name, extraction.error or "Unknown error")
        return None
    actual_raw_path, raw_error = optimizer_support.validated_direct_raw_output(
        engine,
        extraction.document_raw_path,
        raw_dest=raw_dest,
        allowed_roots=ctx.managed_roots,
        display_name=display_name,
    )
    if raw_error or actual_raw_path is None:
        error_workflow.handle_failure(engine, record, ctx, stage_name, raw_error or "Optimizer raw output is missing.")
        return None
    raw_outputs, raw_outputs_error = optimizer_support.validated_direct_raw_outputs(
        engine,
        extraction.page_raw_paths or [extraction.document_raw_path],
        raw_dest=raw_dest,
        allowed_roots=ctx.managed_roots,
        display_name=display_name,
    )
    if raw_outputs_error:
        error_workflow.handle_failure(engine, record, ctx, stage_name, raw_outputs_error)
        return None
    page_paths, page_error = optimizer_support.validated_direct_page_images(
        engine,
        extraction.page_asset_paths,
        page_dir=page_dir,
        allowed_roots=ctx.managed_roots,
        display_name=display_name,
    )
    if page_error:
        error_workflow.handle_failure(engine, record, ctx, stage_name, page_error)
        return None
    record.artifacts.optimizer_raw_paths = [str(path) for path in raw_outputs]
    record.artifacts.optimizer_page_image_paths = [str(path) for path in page_paths]
    record.artifacts.optimizer_ocr_request_paths = list(extraction.ocr_request_paths)
    record.artifacts.optimizer_ocr_request_path = record.artifacts.optimizer_ocr_request_paths[0] if record.artifacts.optimizer_ocr_request_paths else ""
    final_raw_paths = raw_outputs
    record.last_stage = stage_name
    record.touch()
    storage_repository.save_state(engine)
    detail_name = final_raw_paths[0].name if len(final_raw_paths) == 1 else f"{len(final_raw_paths)} page raws"
    debug.set_stage(engine, stage_name, "Done", f"{record.route_family} | {display_name} | {detail_name}")
    debug.emit_snapshot(engine)
    debug.check_cancelled(engine)
    return final_raw_paths
