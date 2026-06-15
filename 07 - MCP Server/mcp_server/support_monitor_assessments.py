"""Assessment records and reportability rules for support incidents."""

from __future__ import annotations

from typing import Any

from . import support_monitor
from .support_monitor_events import incidents_from_events
from .support_monitor_redaction import hash_text, redact, redact_text
from .support_monitor_storage import append_jsonl, assessments_path, load_assessments, load_events, now, required_text
from .support_monitor_types import SupportError

SUPPORT_CLASSIFICATIONS = (
    "missing_path",
    "invalid_user_input",
    "missing_configuration",
    "expected_preflight_failure",
    "permission_denied",
    "external_dependency_failure",
    "unexpected_exception",
    "contract_regression",
    "repeatable_product_failure",
    "data_corruption_risk",
    "unknown",
)
REPORTABLE_CLASSIFICATIONS = {
    "unexpected_exception",
    "contract_regression",
    "repeatable_product_failure",
    "data_corruption_risk",
}
CONFIDENCE_LEVELS = {"low", "medium", "high"}


def assess_incident(payload: dict[str, Any]) -> dict[str, Any]:
    _sync()
    classification = required_text(payload.get("classification"), "classification")
    if classification not in SUPPORT_CLASSIFICATIONS:
        raise SupportError(f"classification must be one of: {', '.join(SUPPORT_CLASSIFICATIONS)}")
    confidence = str(payload.get("confidence") or "low").strip().lower()
    if confidence not in CONFIDENCE_LEVELS:
        raise SupportError("confidence must be one of: low, medium, high")

    reportable = classification in REPORTABLE_CLASSIFICATIONS
    incident_id = str(payload.get("incident_id") or "").strip()
    incident: dict[str, Any] | None = _find_incident(incident_id) if incident_id else None
    event: dict[str, Any] | None = None
    event_payload = _assessment_event_payload(payload)
    if incident_id and incident is None:
        raise SupportError(f"Unknown incident_id: {incident_id}")
    if reportable and not incident_id:
        if not event_payload:
            raise SupportError("reportable assessments require incident_id or event/module_key payload.")
        recorded = support_monitor.record_event(event_payload)
        event = recorded.get("event") if isinstance(recorded.get("event"), dict) else None
        incident = recorded.get("incident") if isinstance(recorded.get("incident"), dict) else None
        incident_id = str((incident or {}).get("incident_id") or "")

    assessment = _assessment_payload(payload, classification, confidence, reportable, incident_id, event)
    append_jsonl(assessments_path(), assessment)
    return {
        "status": "ok",
        "assessment": assessment,
        "reportable": reportable,
        "may_preview_report": bool(reportable and incident_id),
        "next_actions": _next_actions(reportable=reportable, incident_id=incident_id),
    }


def require_assessment(assessment_id: object) -> dict[str, Any]:
    _sync()
    text = required_text(assessment_id, "assessment_id")
    for item in reversed(load_assessments()):
        if str(item.get("assessment_id") or "") == text:
            return item
    raise SupportError(f"Unknown assessment_id: {text}")


def require_reportable_assessment(assessment_id: object) -> dict[str, Any]:
    assessment = require_assessment(assessment_id)
    if not bool(assessment.get("reportable")):
        classification = str(assessment.get("classification") or "unknown")
        raise SupportError(f"assessment_id is not reportable: {classification}")
    incident_id = str(assessment.get("incident_id") or "").strip()
    if not incident_id:
        raise SupportError("assessment_id is reportable but has no incident_id.")
    if _find_incident(incident_id) is None:
        raise SupportError(f"assessment_id references an unknown incident_id: {incident_id}")
    return assessment


def _assessment_payload(
    payload: dict[str, Any],
    classification: str,
    confidence: str,
    reportable: bool,
    incident_id: str,
    event: dict[str, Any] | None,
) -> dict[str, Any]:
    created_at = now()
    summary = redact_text(str(payload.get("user_visible_summary") or payload.get("summary") or payload.get("message") or ""))
    return {
        "schema_version": 1,
        "assessment_id": hash_text(f"{created_at}|{classification}|{confidence}|{incident_id}|{summary}")[:16],
        "created_at": created_at,
        "classification": classification,
        "confidence": confidence,
        "reportable": reportable,
        "incident_id": incident_id,
        "event_id": str((event or {}).get("event_id") or ""),
        "module_key": str((event or {}).get("module_key") or payload.get("module_key") or ""),
        "action": str((event or {}).get("action") or payload.get("tool_action") or ""),
        "user_visible_summary": summary,
        "evidence": redact(payload.get("evidence") if isinstance(payload.get("evidence"), list) else []),
        "blocked_reason": "" if reportable else _blocked_reason(classification),
        "developer_next_action": _developer_next_action(classification),
        "required_user_confirmation": bool(reportable),
    }


def _assessment_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("event")
    if isinstance(event, dict):
        return dict(event)
    module_key = str(payload.get("module_key") or "").strip()
    if not module_key:
        return {}
    classification = str(payload.get("classification") or "").strip()
    severity = str(payload.get("severity") or "").strip() or ("critical" if classification == "data_corruption_risk" else "error")
    return {
        "module_key": module_key,
        "action": str(payload.get("tool_action") or "").strip(),
        "severity": severity,
        "status": str(payload.get("status") or "exception").strip() or "exception",
        "message": str(payload.get("message") or payload.get("user_visible_summary") or classification),
        "exception_type": str(payload.get("exception_type") or "").strip(),
        "stacktrace": str(payload.get("stacktrace") or ""),
        "redaction_class": str(payload.get("redaction_class") or "support_safe").strip() or "support_safe",
        "artifact_refs": payload.get("artifact_refs") if isinstance(payload.get("artifact_refs"), list) else [],
        "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    }


def _find_incident(incident_id: str) -> dict[str, Any] | None:
    if not incident_id:
        return None
    incidents = incidents_from_events(load_events(), dismissed=set())
    return next((item for item in incidents if item.get("incident_id") == incident_id), None)


def _blocked_reason(classification: str) -> str:
    return {
        "missing_path": "Missing work paths are setup or configuration issues, not product bugs.",
        "invalid_user_input": "Invalid input should be explained to the user instead of reported as a bug.",
        "missing_configuration": "Missing configuration needs setup guidance before a support report.",
        "expected_preflight_failure": "Expected preflight failures are normal guardrails.",
        "permission_denied": "Permission denials are not reportable without evidence of a system fault.",
        "external_dependency_failure": "External dependency failures need retry or environment checks first.",
        "unknown": "Unknown incidents need more evidence before a report is useful.",
    }.get(classification, "")


def _developer_next_action(classification: str) -> str:
    if classification in REPORTABLE_CLASSIFICATIONS:
        return "Preview the redacted report, ask the user for confirmation, then queue it locally if approved."
    return "Explain the likely user-actionable fix and do not queue a bug report."


def _next_actions(*, reportable: bool, incident_id: str) -> list[str]:
    if reportable and incident_id:
        return ["preview", "build", "queue"]
    if reportable:
        return ["assess_with_incident_or_event"]
    return ["explain_to_user", "dismiss_if_no_longer_relevant"]


def _sync() -> None:
    support_monitor._sync_state_root()


__all__ = ["assess_incident", "require_assessment", "require_reportable_assessment"]
