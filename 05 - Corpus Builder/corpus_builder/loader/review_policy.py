"""Review and provenance policy for loader domain shaping."""

from __future__ import annotations

from .types import JsonDict


def derive_field_provenance(raw_fields: object, validation_report: JsonDict) -> dict[str, tuple[str, str]]:
    if not isinstance(raw_fields, dict):
        return {}
    refs = raw_fields.get("_source_refs") or {}
    conflicts = {
        str(issue.get("field") or issue.get("key")).lower()
        for issue in validation_report.get("issues", [])
        if isinstance(issue, dict)
        and issue.get("type") == "source_ref_mismatch"
        and (issue.get("field") or issue.get("key"))
    }
    return {
        key: ("conflict", "ocr_only")
        if key.lower() in conflicts and key in refs
        else ("confirmed", "ocr_confirmed")
        if key in refs
        else ("unconfirmed", "vision")
        for key in raw_fields
        if not str(key).startswith("_")
    }


def _parse_optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float) and value.is_integer():
        return int(value) != 0
    if isinstance(value, str):
        return {
            "": False,
            "1": True,
            "true": True,
            "yes": True,
            "y": True,
            "on": True,
            "0": False,
            "false": False,
            "no": False,
            "n": False,
            "off": False,
        }.get(value.strip().lower())
    return None


def coerce_issue_count(validation_report: JsonDict) -> int:
    summary = validation_report.get("summary")
    issues = validation_report.get("issues")
    try:
        return max(0, int(summary.get("total_issues"))) if isinstance(summary, dict) else 0
    except (TypeError, ValueError):
        return len(issues) if isinstance(issues, list) else 0


def effective_needs_review(processing: JsonDict, validation_report: JsonDict, issue_count: int) -> bool:
    explicit = _parse_optional_bool(validation_report.get("needs_review"))
    if explicit is not None:
        return explicit
    status = str(validation_report.get("result", "")).strip().lower()
    fallback = _parse_optional_bool(processing.get("needs_review"))
    if status:
        if status in {"warn", "fail", "error"}:
            return True
        if fallback is not None:
            return fallback
        return False
    return issue_count > 0 if fallback is None else fallback


def payload_review_state(payload: JsonDict) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, ""
    processing = payload.get("processing") if isinstance(payload.get("processing"), dict) else {}
    needs_review = _parse_optional_bool(processing.get("needs_review"))
    if needs_review is None:
        needs_review = _parse_optional_bool(payload.get("needs_review"))
    reason = str(processing.get("review_reason") or payload.get("review_reason") or "").strip()
    return bool(needs_review), reason


def overall_needs_review(
    *,
    structured_payload: JsonDict,
    normalized_payload: JsonDict | None,
    validation_report: JsonDict,
    issue_count: int,
) -> bool:
    structured_review, _ = payload_review_state(structured_payload)
    normalized_review, _ = payload_review_state(normalized_payload or {})
    processing = (
        normalized_payload.get("processing")
        if isinstance(normalized_payload, dict) and isinstance(normalized_payload.get("processing"), dict)
        else {}
    )
    return structured_review or normalized_review or effective_needs_review(processing, validation_report, issue_count)


__all__ = [
    "coerce_issue_count",
    "derive_field_provenance",
    "effective_needs_review",
    "overall_needs_review",
    "payload_review_state",
]
