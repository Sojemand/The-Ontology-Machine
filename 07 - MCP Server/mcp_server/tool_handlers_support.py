from __future__ import annotations

from .atomic_io import atomic_json_write
from .tool_handler_deps import *

_ASSESS_SUPPORT_INCIDENT_ARGUMENTS = {
    "classification",
    "confidence",
    "incident_id",
    "event",
    "module_key",
    "tool_action",
    "severity",
    "status",
    "message",
    "exception_type",
    "stacktrace",
    "redaction_class",
    "artifact_refs",
    "metadata",
    "user_visible_summary",
    "evidence",
}
_LIST_SUPPORT_INCIDENTS_ARGUMENTS = {"show_dismissed", "limit"}
_PREVIEW_REPORT_ARGUMENTS = {"assessment_id", "user_note", "with_recent_events"}
_BUILD_REPORT_ARGUMENTS = {"assessment_id", "user_note", "with_recent_events", "output_path"}
_QUEUE_REPORT_ARGUMENTS = {"assessment_id", "report_path", "destination", "user_confirmed"}
_DISMISS_SUPPORT_INCIDENT_ARGUMENTS = {"incident_id", "reason"}


def assess_support_incident(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _ASSESS_SUPPORT_INCIDENT_ARGUMENTS, "assess_support_incident")
    return support_monitor.assess_incident(arguments)


def list_support_incidents(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _LIST_SUPPORT_INCIDENTS_ARGUMENTS, "list_support_incidents")
    show_dismissed = _optional_bool(arguments, "show_dismissed", default=False)
    limit = _positive_int(arguments["limit"], "limit") if "limit" in arguments and arguments["limit"] not in (None, "") else 20
    return support_monitor.list_incidents(include_dismissed=show_dismissed, limit=limit)


def preview_support_bug_report(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _PREVIEW_REPORT_ARGUMENTS, "preview_support_bug_report")
    assessment = support_monitor.require_reportable_assessment(arguments.get("assessment_id"))
    result = support_monitor.preview_bug_report(
        incident_id=str(assessment["incident_id"]),
        user_note=_optional_text(arguments, "user_note"),
        include_recent_events=_optional_bool(arguments, "with_recent_events", default=True),
    )
    result["report"]["support_assessment"] = assessment
    result["assessment"] = assessment
    return result


def build_support_bug_report(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _BUILD_REPORT_ARGUMENTS, "build_support_bug_report")
    assessment = support_monitor.require_reportable_assessment(arguments.get("assessment_id"))
    result = support_monitor.build_bug_report(
        incident_id=str(assessment["incident_id"]),
        user_note=_optional_text(arguments, "user_note"),
        include_recent_events=_optional_bool(arguments, "with_recent_events", default=True),
        output_path=_optional_text(arguments, "output_path"),
    )
    result["report"]["support_assessment"] = assessment
    atomic_json_write(Path(result["report_path"]), result["report"], indent=2, trailing_newline=True)
    result["assessment"] = assessment
    return result


def queue_support_bug_report(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _QUEUE_REPORT_ARGUMENTS, "queue_support_bug_report")
    assessment = support_monitor.require_reportable_assessment(arguments.get("assessment_id"))
    if not _optional_bool(arguments, "user_confirmed", default=False):
        raise ToolFailure("user_confirmed=true is required before queueing a local support report.")
    report_path = _required_text(arguments, "report_path")
    return support_monitor.submit_bug_report(
        incident_id=str(assessment["incident_id"]),
        report_path=report_path,
        destination=_optional_text(arguments, "destination") or "local_outbox",
    )


def record_support_event(arguments: dict[str, Any]) -> dict[str, Any]:
    return support_monitor.record_event(arguments)


def dismiss_support_incident(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _DISMISS_SUPPORT_INCIDENT_ARGUMENTS, "dismiss_support_incident")
    return support_monitor.dismiss_incident(
        incident_id=_required_text(arguments, "incident_id"),
        reason=_optional_text(arguments, "reason"),
    )


def _reject_unknown(arguments: dict[str, Any], allowed: set[str], tool_name: str) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")

__all__ = [name for name in globals() if not name.startswith("__")]
