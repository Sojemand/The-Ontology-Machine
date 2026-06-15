"""Route-aware intake and queue preparation for pipeline records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import policy_store
from ..integrations import module_entry
from . import debug, error_workflow, route_policy, storage_repository
from .route_types import IntakeDecision, is_route_family

INTAKE_STAGE_NAME = "Intake"


def prepare_pending_queue(engine: Any, records: list[Any], ctx: Any) -> list[Any]:
    ready: list[Any] = []
    for record in records:
        if prepare_record_for_processing(engine, record, ctx, emit_stage=False):
            ready.append(record)
    return ready


def prepare_record_for_processing(engine: Any, record: Any, ctx: Any, *, emit_stage: bool) -> bool:
    _apply_snapshot_metadata(engine, record)
    if emit_stage:
        debug.set_stage(engine, INTAKE_STAGE_NAME, "Processing...", record.file_name)
        debug.emit_snapshot(engine)
    decision = _existing_decision(record) or _classify_record(engine, record)
    _apply_decision(record, decision)
    _apply_snapshot_metadata(engine, record)
    record.last_stage = INTAKE_STAGE_NAME
    record.touch()
    storage_repository.save_state(engine)
    detail = describe_route(record)
    if decision.processable:
        debug.set_stage(engine, INTAKE_STAGE_NAME, "Done", detail)
        debug.emit_snapshot(engine)
        return True
    _route_intake_error(engine, record, ctx, decision)
    return False


def required_live_modules(records: list[Any], default_order: tuple[str, ...]) -> tuple[str, ...]:
    needed = set(policy_store.global_required_modules())
    for record in records:
        for module_key in (record.optimizer_module_key, record.interpreter_module_key):
            if module_key:
                needed.add(module_key)
    return tuple(module_key for module_key in default_order if module_key in needed)


def describe_route(record: Any) -> str:
    route_text = record.route_family or "-"
    optimizer_text = _module_name(record.optimizer_module_key, getattr(record, "optimizer_profile", ""))
    interpreter_text = _module_name(record.interpreter_module_key, getattr(record, "interpreter_profile", ""))
    reason_text = str(record.intake_reason or "").strip() or "-"
    return f"{route_text} | {optimizer_text} | {interpreter_text} | {reason_text}"


def _existing_decision(record: Any) -> IntakeDecision | None:
    if (
        is_route_family(record.route_family)
        and record.optimizer_module_key
        and record.interpreter_module_key
        and getattr(record, "optimizer_profile", "")
        and getattr(record, "interpreter_profile", "")
    ):
        return IntakeDecision(
            route_family=record.route_family,
            optimizer_profile=record.optimizer_profile,
            interpreter_profile=record.interpreter_profile,
            optimizer_module_key=record.optimizer_module_key,
            interpreter_module_key=record.interpreter_module_key,
            intake_reason=record.intake_reason,
        )
    return None


def _classify_record(engine: Any, record: Any) -> IntakeDecision:
    source_path = Path(record.source_path or record.original_source_path or record.file_name)
    suffix = route_policy.normalized_suffix(source_path)
    route_family = route_policy.route_family_for_suffix(suffix)
    if suffix == route_policy.pdf_suffix():
        return _classify_pdf(engine, source_path)
    if route_family == policy_store.route_families()[0] and suffix in route_policy.image_suffixes():
        return IntakeDecision(
            route_family=policy_store.route_families()[0],
            optimizer_profile="vision",
            interpreter_profile="vision",
            optimizer_module_key="optimizer",
            interpreter_module_key="interpreter",
            intake_reason=f"Raster image {suffix} detected.",
        )
    if route_family == policy_store.route_families()[0]:
        return IntakeDecision(
            route_family=policy_store.route_families()[0],
            optimizer_profile="file",
            interpreter_profile="file",
            optimizer_module_key="optimizer",
            interpreter_module_key="interpreter",
            intake_reason=f"File format {suffix} detected.",
        )
    label = suffix or source_path.name or "unknown"
    return IntakeDecision(
        intake_reason=f"Unsupported format {label}.",
        error=f"Unsupported format in Intake: {label}",
        final_error=True,
    )


def _classify_pdf(engine: Any, source_path: Path) -> IntakeDecision:
    result = engine._modules.classify_document(source_path)
    if result.status != "ok":
        return IntakeDecision(
            intake_reason="PDF classification failed.",
            error=result.error or "PDF classification failed.",
        )
    born_digital = policy_store.pdf_classification("born_digital")
    scan = policy_store.pdf_classification("scan")
    if result.classification == born_digital:
        routing = policy_store.pdf_route(born_digital)
        return IntakeDecision(
            route_family=str(routing["route_family"]),
            optimizer_profile="file",
            interpreter_profile="file",
            optimizer_module_key=str(routing["optimizer_module_key"]),
            interpreter_module_key=str(routing["interpreter_module_key"]),
            intake_reason=result.reason or "Born-digital PDF detected.",
        )
    if result.classification == scan:
        routing = policy_store.pdf_route(scan)
        return IntakeDecision(
            route_family=str(routing["route_family"]),
            optimizer_profile="vision",
            interpreter_profile="vision",
            optimizer_module_key=str(routing["optimizer_module_key"]),
            interpreter_module_key=str(routing["interpreter_module_key"]),
            intake_reason=result.reason or "Scanned PDF detected.",
        )
    return IntakeDecision(
        intake_reason="Unexpected PDF classification.",
        error=f"Invalid PDF classification: {result.classification or 'empty'}",
    )


def _apply_decision(record: Any, decision: IntakeDecision) -> None:
    record.route_family = decision.route_family
    record.optimizer_profile = decision.optimizer_profile
    record.interpreter_profile = decision.interpreter_profile
    record.optimizer_module_key = decision.optimizer_module_key
    record.interpreter_module_key = decision.interpreter_module_key
    record.intake_reason = decision.intake_reason


def _apply_snapshot_metadata(engine: Any, record: Any) -> None:
    engine._snapshot.current_route_family = record.route_family
    engine._snapshot.current_optimizer_module = _module_name(record.optimizer_module_key, getattr(record, "optimizer_profile", ""))
    engine._snapshot.current_interpreter_module = _module_name(record.interpreter_module_key, getattr(record, "interpreter_profile", ""))
    engine._snapshot.current_intake_reason = record.intake_reason


def _route_intake_error(engine: Any, record: Any, ctx: Any, decision: IntakeDecision) -> None:
    record.failed_attempts += 1
    reason = decision.error or "Intake failed."
    final = decision.final_error or record.failed_attempts >= engine._max_failed_attempts
    debug.set_stage(engine, INTAKE_STAGE_NAME, "Error", f"{describe_route(record)} | {reason}")
    debug.append_log(engine, f"[ERROR] {record.relative_path}: {INTAKE_STAGE_NAME} -> {reason}")
    error_workflow.route_to_error(engine, record, ctx, stage=INTAKE_STAGE_NAME, reason=reason, final=final)


def _module_name(module_key: str, profile: str = "") -> str:
    if not module_key:
        return "-"
    display_name = module_entry(module_key).display_name
    profile_text = str(profile or "").strip()
    return f"{display_name} [{profile_text}]" if profile_text else display_name
