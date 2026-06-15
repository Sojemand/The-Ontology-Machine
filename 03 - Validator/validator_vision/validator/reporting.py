"""Report assembly for validator workflow results."""
from __future__ import annotations

from ..models.config import ValidatorConfig
from ..models.results import CheckResult, CheckSummary, Summary, ValidationReport
from ..models.types import StructuredDocument


def build_validation_report(
    *,
    document: StructuredDocument,
    check_results: list[CheckResult],
    config: ValidatorConfig,
    validator_version: str,
    validated_at: str,
    processing_time_ms: int,
) -> ValidationReport:
    summary = Summary()
    checks: dict[str, CheckSummary] = {}
    issues_for_report = []

    for result in check_results:
        checks[result.name] = CheckSummary(
            status=result.status,
            issue_count=len(result.issues),
            checked=result.checked,
            valid=result.valid,
        )
        summary.total_issues += len(result.issues)
        summary.fail_count += sum(1 for issue in result.issues if issue.level == "FAIL")
        summary.warn_count += sum(1 for issue in result.issues if issue.level == "WARN")
        summary.checked_values += result.checked
        summary.valid_values += result.valid
        issues_for_report.extend(result.issues[: config.max_issues_per_check])

    report = ValidationReport(
        interpreter_profile=document.interpreter_profile,
        file_name=document.file_name,
        file_path=document.file_path,
        content_hash=document.content_hash,
        validated_at=validated_at,
        validator_version=validator_version,
        processing_time_ms=processing_time_ms,
        result=overall_result(check_results),
        needs_review=False,
        summary=summary,
        checks=checks,
        issues=issues_for_report,
    )
    if config.flag_needs_review and report.result in {"WARN", "FAIL"}:
        report.needs_review = True
    return report


def overall_result(check_results: list[CheckResult]) -> str:
    statuses = [result.status for result in check_results]
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


__all__ = ["build_validation_report", "overall_result"]
