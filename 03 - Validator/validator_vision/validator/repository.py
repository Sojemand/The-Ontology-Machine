"""Persistence helpers for validator workflow outputs."""
from __future__ import annotations

from pathlib import Path

from ..models.report_io import atomic_json_write
from ..models.results import ValidationReport


def write_report(*, report_path: Path | str, report: ValidationReport) -> Path:
    target = Path(report_path)
    atomic_json_write(target, report.to_dict())
    return target
