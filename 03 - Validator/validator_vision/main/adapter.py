"""CLI adapter stage for logging and console output."""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from logging.handlers import RotatingFileHandler

from ..models.config import load_config
from ..models.results import ValidationReport


def setup_logging(
    *,
    ensure_layout: Callable[[], Path],
    resolve_log_dir: Callable[[Path | None], Path],
) -> None:
    file_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root_logger.setLevel(getattr(logging, level, logging.INFO))
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    try:
        logs_path = resolve_log_dir(ensure_layout())
        file_handler = RotatingFileHandler(
            logs_path / "validator_vision.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
    except Exception as exc:
        root_logger.warning("Datei-Logging deaktiviert: %s", exc)
        return

    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)


def load_validator_config(config_path: str | None):
    return load_config(config_path)


def print_error(message: str) -> None:
    print(f"Fehler: {message}")


def print_report_summary(report: ValidationReport) -> None:
    print(f"\n{report.file_name}: {report.result}")
    print(f"  checked={report.summary.checked_values} valid={report.summary.valid_values}")
    print(f"  issues={report.summary.total_issues} needs_review={report.needs_review}")
    if report.issues:
        print("  top issues:")
        for issue in report.issues[:5]:
            print(f"    [{issue.level}] {issue.field}: {issue.message}")


def print_batch_summary(reports: Sequence[ValidationReport]) -> None:
    pass_count = sum(1 for report in reports if report.result == "PASS")
    warn_count = sum(1 for report in reports if report.result == "WARN")
    fail_count = sum(1 for report in reports if report.result == "FAIL")
    print(f"\nFertig: {len(reports)} Dokumente validiert")
    print(f"  PASS={pass_count} WARN={warn_count} FAIL={fail_count}")
