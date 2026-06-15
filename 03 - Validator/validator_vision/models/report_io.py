"""Report and JSON write boundaries for validator serialization."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from .profiles import report_suffix
from .results import CheckSummary, Issue, Summary, ValidationReport

_REPORT_FILENAME_LIMIT = 120
_REPORT_HASH_CHARS = 10


def report_name(structured_path: Path, interpreter_profile: str = "vision") -> str:
    suffix = report_suffix(interpreter_profile)
    name = structured_path.name
    if name.endswith(".structured.json"):
        stem = name[: -len(".structured.json")]
    else:
        stem = structured_path.stem
    return _bounded_report_name(stem, suffix)


def atomic_json_write(
    path: Path,
    data: dict[str, Any],
    *,
    replace_file: Callable[[Path, Path], None] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handle, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=_temp_prefix(path),
        suffix=".tmp",
        text=True,
    )
    tmp_path = Path(tmp_name)
    replace = _replace_file_with_retry if replace_file is None else replace_file
    try:
        with os.fdopen(file_handle, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def validation_report_from_dict(data: dict[str, Any]) -> ValidationReport:
    summary = data.get("summary", {})
    checks = data.get("checks", {})
    issues = data.get("issues", [])
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(checks, dict):
        checks = {}
    if not isinstance(issues, list):
        issues = []

    return ValidationReport(
        schema_version=str(data.get("schema_version", "1.0")),
        interpreter_profile=str(data.get("interpreter_profile", "")),
        file_name=str(data.get("file_name", "")),
        file_path=str(data.get("file_path", "")),
        content_hash=str(data.get("content_hash", "")),
        validated_at=str(data.get("validated_at", "")),
        validator_version=str(data.get("validator_version", "")),
        processing_time_ms=int(data.get("processing_time_ms", 0) or 0),
        result=str(data.get("result", "PASS")),
        needs_review=bool(data.get("needs_review", False)),
        summary=Summary(
            total_issues=int(summary.get("total_issues", 0) or 0),
            fail_count=int(summary.get("fail_count", 0) or 0),
            warn_count=int(summary.get("warn_count", 0) or 0),
            checked_values=int(summary.get("checked_values", 0) or 0),
            valid_values=int(summary.get("valid_values", 0) or 0),
        ),
        checks={
            str(name): CheckSummary(
                status=str(check_summary.get("status", "PASS")),
                issue_count=int(check_summary.get("issue_count", 0) or 0),
                checked=int(check_summary.get("checked", 0) or 0),
                valid=int(check_summary.get("valid", 0) or 0),
            )
            for name, check_summary in checks.items()
            if isinstance(check_summary, dict)
        },
        issues=[
            Issue(
                check=str(issue.get("check", "")),
                level=str(issue.get("level", "")),
                field=str(issue.get("field", "")),
                extracted_value=issue.get("extracted_value"),
                raw_value=issue.get("raw_value"),
                source_ref=issue.get("source_ref"),
                message=str(issue.get("message", "")),
            )
            for issue in issues
            if isinstance(issue, dict)
        ],
    )


def load_report(path: Path) -> ValidationReport:
    from .structured_io import read_json_object

    return validation_report_from_dict(read_json_object(Path(path), label="Report"))


def _replace_file_with_retry(source: Path, target: Path) -> None:
    for attempt in range(8):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.01 * (attempt + 1))


def _temp_prefix(path: Path) -> str:
    digest = hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:8]
    return f".{digest}."


def _bounded_report_name(stem: str, suffix: str) -> str:
    name = stem + suffix
    if len(name) <= _REPORT_FILENAME_LIMIT:
        return name
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:_REPORT_HASH_CHARS]
    stem_budget = _REPORT_FILENAME_LIMIT - len(suffix) - len(digest) - 1
    return f"{stem[:stem_budget]}-{digest}{suffix}"
