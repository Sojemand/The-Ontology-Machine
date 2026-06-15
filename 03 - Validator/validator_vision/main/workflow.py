"""CLI workflow stage for command orchestration."""
from __future__ import annotations

from ..validator import DocumentValidator
from ..validator.planning import build_validation_target, plan_batch_targets
from . import adapter, validation
from .types import ValidateBatchCommand, ValidateCommand


def run_validate(
    command: ValidateCommand,
    *,
    load_validator_config=adapter.load_validator_config,
) -> int:
    try:
        structured_path = validation.require_structured_file(command.structured_path)
        report_path = validation.require_report_path(command.report_path)
        raw_path = validation.require_optional_file(command.raw_path, label="Raw JSON")
        raw_root = validation.require_optional_dir(command.raw_root, label="Raw-Ordner")
    except validation.CliUsageError as exc:
        adapter.print_error(str(exc))
        return 1

    try:
        target = build_validation_target(
            structured_path,
            report_path,
            raw_path=raw_path,
            raw_root=raw_root,
        )
        validator = DocumentValidator(load_validator_config(command.config_path))
        report = validator.validate(
            target.structured_path,
            target.report_path,
            raw_path=target.raw_path,
            document=target.document,
        )
    except Exception as exc:
        adapter.print_error(f"Validierung fehlgeschlagen: {exc}")
        return 1

    adapter.print_report_summary(report)
    return 0


def run_batch(
    command: ValidateBatchCommand,
    *,
    load_validator_config=adapter.load_validator_config,
) -> int:
    try:
        structured_dir = validation.require_structured_dir(command.structured_dir)
        report_root = validation.require_report_root(command.report_root)
        raw_root = validation.require_optional_dir(command.raw_root, label="Raw-Ordner")
    except validation.CliUsageError as exc:
        adapter.print_error(str(exc))
        return 1

    try:
        targets = plan_batch_targets(structured_dir, report_root, raw_root=raw_root)
        validator = DocumentValidator(load_validator_config(command.config_path))
        reports = validator.validate_batch(targets)
    except Exception as exc:
        adapter.print_error(f"Batch-Validierung fehlgeschlagen: {exc}")
        return 1

    adapter.print_batch_summary(reports)
    return 0 if all(report.result != "FAIL" for report in reports) else 2
