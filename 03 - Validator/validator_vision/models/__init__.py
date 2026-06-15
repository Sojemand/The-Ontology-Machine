"""Path-stable surface for validator models, config, and serialization helpers."""
from __future__ import annotations

from .config import CheckToggles, MatchConfig, ValidatorConfig, load_config, resolve_config_path
from .report_io import atomic_json_write, load_report, report_name
from .results import CheckResult, CheckSummary, Issue, Summary, ValidationReport
from .types import PreparedFreeText, StructuredDocument, StructuredRow

__all__ = [
    "CheckResult",
    "CheckSummary",
    "CheckToggles",
    "Issue",
    "MatchConfig",
    "PreparedFreeText",
    "StructuredDocument",
    "StructuredRow",
    "Summary",
    "ValidationReport",
    "ValidatorConfig",
    "atomic_json_write",
    "load_config",
    "load_report",
    "report_name",
    "resolve_config_path",
]
