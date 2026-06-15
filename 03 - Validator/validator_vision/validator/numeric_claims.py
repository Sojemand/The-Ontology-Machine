"""Raw-backed validation for numeric/date claims that must survive into structured output."""
from __future__ import annotations

from ..models.config import MatchConfig
from ..models.results import CheckResult, Issue
from ..models.types import StructuredDocument
from .numeric_claim_types import ClaimEvidence
from .raw_claims import collect_raw_claims
from .structured_claims import collect_structured_claims


def check_numeric_claims(
    document: StructuredDocument,
    raw_payload: dict,
    cfg: MatchConfig,
    *,
    raw_path: str,
) -> CheckResult:
    raw_claims = collect_raw_claims(raw_payload)
    structured_numbers, structured_dates = collect_structured_claims(document.payload)

    issues: list[Issue] = []
    checked = len(raw_claims)
    valid = 0
    for claim in raw_claims.values():
        if _is_supported_by_structured(claim, structured_numbers, structured_dates, cfg.number_tolerance_absolute):
            valid += 1
            continue
        issues.append(_issue_from_claim(claim, raw_path=raw_path))

    return CheckResult(
        name="numeric_claims",
        status=_status_for_issues(issues),
        issues=issues,
        checked=checked,
        valid=valid,
    )


def _issue_from_claim(claim: ClaimEvidence, *, raw_path: str) -> Issue:
    field_paths = sorted(claim.field_paths)
    display_value = claim.display_values[0] if claim.display_values else str(claim.raw_value)
    level = "WARN" if claim.strength == "weak" else "FAIL"
    return Issue(
        check="numeric_claims",
        level=level,
        field=field_paths[0] if field_paths else "raw",
        extracted_value=display_value,
        raw_value=display_value,
        source_ref=raw_path,
        message=_message_from_claim(claim, level=level),
    )


def _is_supported_by_structured(
    claim: ClaimEvidence,
    structured_numbers: list[float],
    structured_dates: set[str],
    tolerance: float,
) -> bool:
    if claim.kind == "date":
        return str(claim.raw_value) in structured_dates
    expected = float(claim.raw_value)
    return any(abs(candidate - expected) <= tolerance + 1e-9 for candidate in structured_numbers)


def _message_from_claim(claim: ClaimEvidence, *, level: str) -> str:
    if level == "WARN":
        return (
            "Unsicherer numerischer Raw-Claim aus schwacher Evidence fehlt im Structured."
            if claim.kind == "number"
            else "Unsicherer Datums-Claim aus schwacher Evidence fehlt im Structured."
        )
    return (
        "Numerischer Raw-Claim fehlt im Structured."
        if claim.kind == "number"
        else "Datums-Claim aus dem Raw fehlt im Structured."
    )


def _status_for_issues(issues: list[Issue]) -> str:
    if any(issue.level == "FAIL" for issue in issues):
        return "FAIL"
    if issues:
        return "WARN"
    return "PASS"


__all__ = ["check_numeric_claims"]
