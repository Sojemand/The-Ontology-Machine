"""Assessment-gated support workflow for the agent-visible tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .atomic_io import atomic_json_write
from . import support_monitor
from .support_monitor_assessments import assess_incident, require_assessment, require_reportable_assessment
from .support_monitor_storage import required_text
from .support_monitor_types import SupportError


def run(payload: dict[str, Any], *, action_field: str = "action") -> dict[str, Any]:
    _sync()
    if not isinstance(payload, dict):
        raise SupportError("support incident workflow payload must be a JSON object.")
    action = required_text(payload.get(action_field), action_field)
    if action == "assess":
        return assess_incident(payload)
    if action == "list":
        return support_monitor.list_incidents(
            include_dismissed=_bool(payload.get("include_dismissed"), default=False, field="include_dismissed"),
            limit=_positive_int(payload.get("limit", 20), field="limit"),
        )
    if action == "preview":
        assessment = require_reportable_assessment(payload.get("assessment_id"))
        return _preview_with_assessment(
            assessment,
            incident_id=str(assessment["incident_id"]),
            user_note=str(payload.get("user_note") or ""),
            include_recent_events=_bool(payload.get("include_recent_events"), default=True, field="include_recent_events"),
        )
    if action == "build":
        assessment = require_reportable_assessment(payload.get("assessment_id"))
        return _build_with_assessment(
            assessment,
            incident_id=str(assessment["incident_id"]),
            user_note=str(payload.get("user_note") or ""),
            include_recent_events=_bool(payload.get("include_recent_events"), default=True, field="include_recent_events"),
            output_path=str(payload.get("output_path") or ""),
        )
    if action == "queue":
        return _queue_assessed_report(payload)
    if action == "dismiss":
        return _dismiss_assessed_incident(payload)
    raise SupportError(f"Unknown support workflow action: {action}")


def _queue_assessed_report(payload: dict[str, Any]) -> dict[str, Any]:
    assessment = require_reportable_assessment(payload.get("assessment_id"))
    if not _bool(payload.get("user_confirmed"), default=False, field="user_confirmed"):
        raise SupportError("user_confirmed=true is required before queueing a local support report.")
    report_path = required_text(payload.get("report_path"), "report_path")
    return support_monitor.submit_bug_report(
        incident_id=str(assessment["incident_id"]),
        report_path=report_path,
        destination=str(payload.get("destination") or "local_outbox"),
    )


def _dismiss_assessed_incident(payload: dict[str, Any]) -> dict[str, Any]:
    assessment_id = str(payload.get("assessment_id") or "").strip()
    incident_id = str(payload.get("incident_id") or "").strip()
    if assessment_id:
        assessment = require_assessment(assessment_id)
        incident_id = str(assessment.get("incident_id") or incident_id)
    return support_monitor.dismiss_incident(incident_id=incident_id, reason=str(payload.get("reason") or ""))


def _preview_with_assessment(assessment: dict[str, Any], *, incident_id: str, user_note: str = "", include_recent_events: bool = True) -> dict[str, Any]:
    result = support_monitor.preview_bug_report(incident_id=incident_id, user_note=user_note, include_recent_events=include_recent_events)
    result["report"]["support_assessment"] = assessment
    result["assessment"] = assessment
    return result


def _build_with_assessment(assessment: dict[str, Any], *, incident_id: str, user_note: str = "", include_recent_events: bool = True, output_path: str = "") -> dict[str, Any]:
    result = support_monitor.build_bug_report(incident_id=incident_id, user_note=user_note, include_recent_events=include_recent_events, output_path=output_path)
    result["report"]["support_assessment"] = assessment
    atomic_json_write(Path(result["report_path"]), result["report"], indent=2, trailing_newline=True)
    result["assessment"] = assessment
    return result


def _bool(value: object, *, default: bool, field: str) -> bool:
    if value is None or value == "":
        return default
    if not isinstance(value, bool):
        raise SupportError(f"{field} must be true or false.")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool):
        raise SupportError(f"{field} must be a positive integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise SupportError(f"{field} must be a positive integer.") from None
    if parsed < 1:
        raise SupportError(f"{field} must be a positive integer.")
    return parsed


def _sync() -> None:
    support_monitor._sync_state_root()


__all__ = ["run"]
