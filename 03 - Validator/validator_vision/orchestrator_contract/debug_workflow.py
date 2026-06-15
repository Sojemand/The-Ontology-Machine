"""Headless debug-run workflow for validator orchestrator sessions."""

from __future__ import annotations

from copy import deepcopy
from inspect import signature
from pathlib import Path

from ..models.profiles import require_supported_profile
from ..models.report_io import report_name
from ..validator import adapter as validator_adapter
from ..validator.planning import build_validation_target, plan_batch_targets
from . import debug_support


def run_debug(command, *, load_config_fn, validator_cls) -> dict:
    session_root = command.session_root
    output_root = command.output_root
    session_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    if debug_support.cancel_requested(session_root):
        return _cancelled(session_root, output_root, [], total=0, detail="Debuglauf abgebrochen")
    try:
        config = _apply_check_toggles(load_config_fn(), command.check_toggles)
        debug_support.write_config_snapshot(output_root, config)
        validator = validator_cls(config)
        report_records, total, cancelled = _run_targets(command, session_root, output_root, validator)
        debug_support.write_report_index(output_root, session_root, report_records)
    except Exception as exc:
        message = str(exc)
        debug_support.append_log(session_root, f"[ERROR] {message}")
        debug_support.write_snapshot(session_root, status="error", detail=message)
        return debug_support.write_result(
            session_root,
            {"status": "error", "summary": "Debuglauf fehlgeschlagen", "error": message},
        )
    reports = _reports_from_records(report_records)
    if cancelled:
        return _cancelled(session_root, output_root, report_records, total=total, detail="Debuglauf abgebrochen")
    outputs = debug_support.collect_outputs(
        session_root,
        output_root,
        report_paths=_paths_from_records(report_records),
    )
    metrics = debug_support.counters_from_reports(reports)
    summary = debug_support.summary_text(reports)
    debug_support.write_snapshot(
        session_root,
        status="ok",
        detail=summary,
        processed=len(reports),
        total=total,
        counters=metrics,
    )
    debug_support.append_log(session_root, f"[RUN] {summary}")
    return debug_support.write_result(
        session_root,
        {"status": "ok", "summary": summary, "outputs": outputs, "metrics": metrics},
    )


def _run_targets(command, session_root: Path, output_root: Path, validator) -> tuple[list[tuple[Path, object]], int, bool]:
    accepts_document = _validator_accepts_document(validator)
    if command.mode == "single":
        document = validator_adapter.load_structured_document(command.source_path)
        report_path = _single_report_path(command.source_path, output_root, document=document)
        target = build_validation_target(
            command.source_path,
            report_path,
            raw_path=command.raw_path,
            raw_root=command.raw_root,
            document=document,
        )
        debug_support.write_snapshot(session_root, status="running", detail=target.structured_path.name, total=1)
        report = _validate_target(validator, target, accepts_document=accepts_document)
        debug_support.append_log(session_root, _report_log_line(report))
        return [(target.report_path, report)], 1, debug_support.cancel_requested(session_root)
    targets = plan_batch_targets(command.input_root, debug_support.report_root(output_root), raw_root=command.raw_root)
    report_records: list[tuple[Path, object]] = []
    total = len(targets)
    for index, target in enumerate(targets, start=1):
        if debug_support.cancel_requested(session_root):
            return report_records, total, True
        reports = _reports_from_records(report_records)
        debug_support.write_snapshot(
            session_root,
            status="running",
            detail=target.structured_path.name,
            processed=index - 1,
            total=total,
            counters=debug_support.counters_from_reports(reports),
        )
        report = _validate_target(validator, target, accepts_document=accepts_document)
        report_records.append((target.report_path, report))
        debug_support.append_log(session_root, _report_log_line(report))
    return report_records, total, debug_support.cancel_requested(session_root)


def _single_report_path(structured_path: Path, output_root: Path, *, document=None) -> Path:
    if document is None:
        document = validator_adapter.load_structured_document(structured_path)
    profile = require_supported_profile(document.interpreter_profile)
    return debug_support.report_root(output_root) / report_name(structured_path, profile)


def _validator_accepts_document(validator) -> bool:
    return "document" in signature(validator.validate).parameters


def _validate_target(validator, target, *, accepts_document: bool):
    if accepts_document:
        return validator.validate(
            target.structured_path,
            target.report_path,
            raw_path=target.raw_path,
            document=target.document,
        )
    return validator.validate(target.structured_path, target.report_path, raw_path=target.raw_path)


def _apply_check_toggles(config, overrides: dict[str, bool]):
    updated = deepcopy(config)
    for key, value in overrides.items():
        setattr(updated.checks, key, bool(value))
    return updated


def _cancelled(session_root: Path, output_root: Path, report_records: list[tuple[Path, object]], *, total: int, detail: str) -> dict:
    reports = _reports_from_records(report_records)
    metrics = debug_support.counters_from_reports(reports)
    outputs = debug_support.collect_outputs(
        session_root,
        output_root,
        report_paths=_paths_from_records(report_records),
    )
    debug_support.write_snapshot(
        session_root,
        status="cancelled",
        detail=detail,
        processed=len(reports),
        total=total,
        counters=metrics,
    )
    debug_support.append_log(session_root, f"[CANCELLED] {detail}")
    return debug_support.write_result(
        session_root,
        {"status": "cancelled", "summary": detail, "outputs": outputs, "metrics": metrics},
    )


def _report_log_line(report) -> str:
    return (
        f"[{report.result}] {report.file_name} "
        f"(issues={report.summary.total_issues}, fail={report.summary.fail_count}, warn={report.summary.warn_count})"
    )


def _reports_from_records(report_records: list[tuple[Path, object]]) -> list[object]:
    return [report for _path, report in report_records]


def _paths_from_records(report_records: list[tuple[Path, object]]) -> list[Path]:
    return [path for path, _report in report_records]
