"""Failure routing and success finalization for pipeline records."""

from __future__ import annotations

from typing import Any

from ..integrations import module_entry, stage_name_for_module
from . import artifact_repository, bundle_repository, debug, policy, storage_repository, success_repository


def handle_failure(engine: Any, record: Any, ctx: Any, stage: str, reason: str) -> None:
    record.failed_attempts += 1
    record.last_stage = stage
    record.last_error = reason
    record.touch()
    current = engine._snapshot.stage_statuses.get(stage)
    debug.set_stage(
        engine,
        stage,
        "Error",
        reason,
        progress_current=getattr(current, "progress_current", 0),
        progress_total=getattr(current, "progress_total", 0),
        progress_label=getattr(current, "progress_label", ""),
    )
    debug.append_log(engine, f"[ERROR] {record.relative_path}: {stage} -> {reason}")
    if record.failed_attempts >= engine._max_failed_attempts:
        route_to_error(
            engine,
            record,
            ctx,
            stage=stage,
            reason=f"{reason} (max {engine._max_failed_attempts} errors reached)",
            final=True,
        )
        return
    route_to_error(engine, record, ctx, stage=stage, reason=reason)


def finalize_success(engine: Any, record: Any, ctx: Any, paths: Any) -> bool:
    publish_error = success_repository.publish_success_artifacts(engine, record, ctx)
    if publish_error:
        route_to_error(
            engine,
            record,
            ctx,
            stage=stage_name_for_module("corpus_builder"),
            reason=publish_error,
            final=True,
        )
        return False
    artifact_repository.move_to_originals_archive(engine, record, ctx)
    policy.refresh_record_review_reason(record)
    needs_review = policy.record_needs_review(record)
    record.status = "success"
    record.final_disposition = "needs_review" if needs_review else "success"
    record.current_location = "originals_archive"
    record.last_stage = stage_name_for_module("corpus_builder")
    record.last_error = ""
    if not needs_review:
        policy.clear_record_review_state(record)
    record.touch()
    storage_repository.save_state(engine)
    if needs_review:
        debug.append_log(engine, f"[OK-REVIEW] {record.relative_path} written to corpus.db -> {record.review_reason}")
    else:
        debug.append_log(engine, f"[OK] {record.relative_path} written to corpus.db")
    bundle_repository.copy_run_log_snapshot(
        engine,
        record,
        paths.published_route_root,
        allowed_roots=ctx.managed_roots,
        run_log_path=debug.active_document_log_path(engine) or ctx.run_log_path,
    )
    debug.recompute_snapshot_counts(engine, ctx.tracked_hashes)
    debug.emit_snapshot(engine)
    return True


def route_to_error(
    engine: Any,
    record: Any,
    ctx: Any,
    *,
    stage: str,
    reason: str,
    final: bool = False,
) -> None:
    module_name = _module_name_for_failure(record, stage)
    error_bundle = bundle_repository.bundle_dir(ctx.ui_state, record, stage=stage, module_name=module_name)
    source_in_bundle = bundle_repository.move_source_into_bundle(engine, record, error_bundle, allowed_roots=ctx.managed_roots)
    frozen = bundle_repository.freeze_bundle_artifacts(
        engine,
        record,
        error_bundle,
        allowed_roots=ctx.managed_roots,
        run_log_path=debug.active_document_log_path(engine) or ctx.run_log_path,
        source_path=source_in_bundle,
    )
    artifact_repository.cleanup_normal_outputs(engine, record, allowed_roots=ctx.managed_roots)
    record.status = "error"
    record.final_disposition = "error" if final else ""
    record.current_location = "error_bundle" if source_in_bundle is not None else record.current_location
    if source_in_bundle is not None:
        record.source_path = str(source_in_bundle)
    record.last_stage = stage
    record.last_error = reason
    record.artifacts.optimizer_raw_paths = list(frozen.optimizer_raw_paths)
    record.artifacts.optimizer_page_image_paths = list(frozen.optimizer_page_image_paths)
    record.artifacts.optimizer_ocr_request_paths = list(frozen.optimizer_ocr_request_paths)
    record.artifacts.optimizer_ocr_request_path = frozen.optimizer_ocr_request_path
    record.artifacts.interpreter_request_paths = list(frozen.interpreter_request_paths)
    record.artifacts.interpreter_request_path = frozen.interpreter_request_path
    record.artifacts.interpreter_debug_bundle_path = frozen.interpreter_debug_bundle_path
    record.artifacts.structured_paths = list(frozen.structured_paths)
    record.artifacts.structured_path = frozen.structured_path
    record.artifacts.validation_report_paths = list(frozen.validation_report_paths)
    record.artifacts.validation_report_path = frozen.validation_report_path
    record.artifacts.normalized_paths = list(frozen.normalized_paths)
    record.artifacts.normalized_path = frozen.normalized_path
    record.artifacts.normalizer_request_paths = list(frozen.normalizer_request_paths)
    record.artifacts.normalizer_request_path = frozen.normalizer_request_path
    record.artifacts.bundle_dir = str(error_bundle)
    record.artifacts.bundle_manifest_path = str(bundle_repository.bundle_manifest_path(engine, record, error_bundle))
    record.touch()
    bundle_repository.write_bundle_manifest(
        engine,
        record,
        error_bundle,
        stage=stage,
        reason=reason,
        disposition="error",
        module_name=module_name,
    )
    storage_repository.save_state(engine)
    debug.recompute_snapshot_counts(engine, ctx.tracked_hashes)
    debug.emit_snapshot(engine)


def _module_name_for_failure(record: Any, stage: str) -> str:
    if stage == "Intake":
        return "Intake"
    if stage == "Runtime Semantics":
        return "Orchestrator"
    if stage == "Request Enrichment":
        return "Orchestrator"
    if stage == "Optimizer" and record.optimizer_module_key:
        return module_entry(record.optimizer_module_key).display_name
    if stage == "Interpreter" and record.interpreter_module_key:
        return module_entry(record.interpreter_module_key).display_name
    if stage == stage_name_for_module("validator"):
        return module_entry("validator").display_name
    if stage == stage_name_for_module("normalizer"):
        return module_entry("normalizer").display_name
    if stage in {stage_name_for_module("corpus_builder"), "Embeddings"}:
        return module_entry("corpus_builder").display_name
    return str(stage or "Unknown").strip() or "Unknown"
