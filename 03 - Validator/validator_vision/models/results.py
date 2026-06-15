"""Named result types for validator reports and check outputs."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Issue:
    check: str
    level: str
    field: str
    extracted_value: Any
    raw_value: Any
    source_ref: str | None
    message: str


@dataclass
class CheckResult:
    name: str
    status: str
    issues: list[Issue] = field(default_factory=list)
    checked: int = 0
    valid: int = 0


@dataclass
class Summary:
    total_issues: int = 0
    fail_count: int = 0
    warn_count: int = 0
    checked_values: int = 0
    valid_values: int = 0


@dataclass
class CheckSummary:
    status: str = "PASS"
    issue_count: int = 0
    checked: int = 0
    valid: int = 0


@dataclass
class ValidationReport:
    schema_version: str = "1.0"
    interpreter_profile: str = ""
    file_name: str = ""
    file_path: str = ""
    content_hash: str = ""
    validated_at: str = ""
    validator_version: str = ""
    processing_time_ms: int = 0
    result: str = "PASS"
    needs_review: bool = False
    summary: Summary = field(default_factory=Summary)
    checks: dict[str, CheckSummary] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationReport":
        from .report_io import validation_report_from_dict

        return validation_report_from_dict(data)
