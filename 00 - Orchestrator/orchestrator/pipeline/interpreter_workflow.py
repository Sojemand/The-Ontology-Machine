"""Interpreter stage workflow for pipeline records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..integrations import module_entry, stage_name_for_module
from . import artifact_repository, debug, document_types, policy, validation
from .page_stage_types import PageStageResult


def run_interpreter_page(
    engine: Any,
    record: Any,
    ctx: Any,
    paths: Any,
    request_path: Path,
    *,
    page_index: int,
    page_total: int,
) -> PageStageResult:
    module_key = record.interpreter_module_key or "interpreter"
    display_name = module_entry(module_key).display_name
    stage_name = stage_name_for_module(module_key)
    input_path, input_error = _interpreter_request_path(engine, record, ctx, request_path)
    if input_path is None:
        return PageStageResult.failure(input_error or "Interpreter request is missing.")
    target_structured_path = _target_structured_path(paths, request_path, request_total=page_total)
    target_debug_dir = _target_debug_dir(paths, request_path, request_total=page_total)
    debug.set_stage(
        engine,
        stage_name,
        "Processing...",
        f"{record.route_family} | {display_name} | {_page_detail(input_path, page_index, page_total)}",
        progress_current=page_index,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    interpretation = engine._modules.interpret_document(
        input_path,
        target_structured_path,
        module_key=module_key,
        interpreter_profile=getattr(record, "interpreter_profile", "") or "vision",
        debug_bundle_dir=target_debug_dir,
    )
    if interpretation.debug_bundle_path:
        record.artifacts.interpreter_debug_bundle_path = str(interpretation.debug_bundle_path)
    if interpretation.status == "error":
        return PageStageResult.failure(interpretation.error or "Unknown error")
    structured_path_text = str(interpretation.structured_path or "").strip()
    if not structured_path_text:
        return PageStageResult.failure("Interpreter did not provide structured output.")
    structured_error = artifact_repository.promote_structured_output(
        engine,
        Path(structured_path_text),
        target_structured_path,
        allowed_roots=ctx.managed_roots,
    )
    if structured_error:
        return PageStageResult.failure(structured_error)
    record.artifacts.structured_paths = [str(target_structured_path)]
    record.artifacts.structured_path = str(target_structured_path)
    debug.check_cancelled(engine)
    structured_payload = load_json(target_structured_path)
    if structured_payload is None:
        return PageStageResult.failure("Interpreter provided invalid structured JSON.", path=target_structured_path)
    review_reason = policy.structured_review_reason(structured_payload) or interpretation.review_reason
    debug.set_stage(
        engine,
        stage_name,
        "Review" if policy.structured_needs_review(structured_payload) else "Done",
        review_reason or _page_detail(target_structured_path, page_index, page_total),
        progress_current=page_index + 1,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    return PageStageResult.success(
        target_structured_path,
        needs_review=policy.structured_needs_review(structured_payload),
        review_stage="interpreter",
        review_reason=review_reason,
    )


def _interpreter_request_path(engine: Any, record: Any, ctx: Any, request_path: Path) -> tuple[Path | None, str]:
    request_text = str(request_path or "").strip()
    if not request_text:
        request_text = str(getattr(record.artifacts, "interpreter_request_path", "") or "").strip()
    return validation.validated_existing_file_path(
        engine,
        request_text,
        allowed_roots=ctx.managed_roots,
        action="Interpreter",
        noun="Interpreter-Request",
        missing_message="Interpreter request is missing.",
    )


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _target_structured_path(paths: Any, request_path: Path, *, request_total: int) -> Path:
    if request_total == 1:
        return paths.working_structured_path
    return document_types.page_structured_path(paths, request_path)


def _target_debug_dir(paths: Any, request_path: Path, *, request_total: int) -> Path:
    if request_total == 1:
        return paths.working_interpreter_debug_dir
    return document_types.page_interpreter_debug_dir(paths, request_path)


def _page_detail(input_path: Path, page_index: int, page_total: int) -> str:
    if page_total <= 1:
        return input_path.name
    return f"Page {page_index + 1}/{page_total} | {input_path.name}"
