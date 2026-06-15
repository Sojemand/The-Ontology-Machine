"""Hard validation boundaries for structured/free-text checks."""
from __future__ import annotations

import math
from typing import Any

from ...models.config import MatchConfig
from ...models.results import CheckResult, Issue
from ...models.types import StructuredDocument


def is_checkable_value(value: Any, cfg: MatchConfig) -> bool:
    if value is None or isinstance(value, (dict, list)):
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, str):
        stripped = value.strip()
        return bool(stripped) and (
            len(stripped) >= cfg.min_string_length or any(char.isdigit() for char in stripped)
        )
    return False


def status_for_issues(issues: list[Issue]) -> str:
    if any(issue.level == "FAIL" for issue in issues):
        return "FAIL"
    if issues:
        return "WARN"
    return "PASS"


def check_free_text_presence(document: StructuredDocument, cfg: MatchConfig) -> CheckResult:
    if document.free_text.is_present:
        return CheckResult(name="free_text", status="PASS", checked=1, valid=1)
    if not cfg.require_free_text:
        return CheckResult(name="free_text", status="PASS", checked=1, valid=0)
    issue = Issue(
        check="free_text",
        level="FAIL",
        field="content.free_text",
        extracted_value=document.free_text.raw_value,
        raw_value=None,
        source_ref=None,
        message="content.free_text fehlt oder ist leer.",
    )
    return CheckResult(name="free_text", status="FAIL", issues=[issue], checked=1, valid=0)


__all__ = ["check_free_text_presence", "is_checkable_value", "status_for_issues"]
