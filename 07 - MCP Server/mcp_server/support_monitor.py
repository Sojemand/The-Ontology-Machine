"""Local support-event and bug-report workflow for installed systems."""

from __future__ import annotations

import json
import re
import shutil
import traceback
from pathlib import Path
from typing import Any

from .atomic_io import atomic_json_write
from .support_monitor_events import incidents_from_events, normalize_event
from .support_monitor_reports import build_report as _build_report
from .support_monitor_redaction import hash_text
from .support_monitor_storage import append_jsonl, dismissed_path, ensure_path_budget, events_path, load_assessments, load_dismissed, load_events, now, outbox_dir, reports_dir, required_text, state_root as _default_state_root
from .support_monitor_types import SupportError
from . import support_monitor_storage as _storage

_QUEUED_REPORT_STEM_MAX_CHARS = 80


def state_root() -> Path:
    return _default_state_root()


def record_event(payload: dict[str, Any]) -> dict[str, Any]:
    _sync_state_root()
    event = normalize_event(payload)
    append_jsonl(events_path(), event)
    incidents = incidents_from_events([event], dismissed=set())
    incident = incidents[0] if incidents else {}
    return {"status": "ok", "event": event, "incident": incident}


def record_exception_event(*, module_key: str, action: str, message: str, exc: BaseException) -> None:
    try:
        record_event({"module_key": module_key, "action": action, "severity": "error", "status": "exception", "message": message, "exception_type": type(exc).__name__, "stacktrace": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), "metadata": {"source": "mcp_tool_handler"}})
    except Exception:
        return


def list_incidents(*, include_dismissed: bool = False, limit: int = 20) -> dict[str, Any]:
    _sync_state_root()
    events = load_events()
    dismissed = load_dismissed()
    incidents = incidents_from_events(events, dismissed=dismissed if not include_dismissed else set())
    incidents.sort(key=lambda item: str(item.get("last_seen") or ""), reverse=True)
    if limit > 0:
        incidents = incidents[:limit]
    return {"status": "ok", "support_state_root": str(state_root()), "event_count": len(events), "incident_count": len(incidents), "dismissed_count": len(dismissed), "incidents": incidents}


def support_incident_workflow(payload: dict[str, Any], *, action_field: str = "action") -> dict[str, Any]:
    from .support_monitor_workflow import run

    return run(payload, action_field=action_field)


def assess_incident(payload: dict[str, Any]) -> dict[str, Any]:
    from .support_monitor_workflow import assess_incident as _assess_incident

    return _assess_incident(payload)


def require_assessment(assessment_id: object) -> dict[str, Any]:
    from .support_monitor_workflow import require_assessment as _require_assessment

    return _require_assessment(assessment_id)


def require_reportable_assessment(assessment_id: object) -> dict[str, Any]:
    from .support_monitor_workflow import require_reportable_assessment as _require_reportable_assessment

    return _require_reportable_assessment(assessment_id)


def preview_bug_report(*, incident_id: str, user_note: str = "", include_recent_events: bool = True) -> dict[str, Any]:
    _sync_state_root()
    return {"status": "ok", "report": _build_report(incident_id, user_note=user_note, include_recent_events=include_recent_events)}


def build_bug_report(*, incident_id: str, user_note: str = "", include_recent_events: bool = True, output_path: str = "") -> dict[str, Any]:
    _sync_state_root()
    report = _build_report(incident_id, user_note=user_note, include_recent_events=include_recent_events)
    target = Path(output_path).expanduser().resolve() if output_path else reports_dir() / f"{incident_id}.bug_report.json"
    ensure_path_budget(target, "support report path")
    atomic_json_write(target, report, indent=2, trailing_newline=True)
    return {"status": "ok", "report_path": str(target), "report": report}


def submit_bug_report(*, incident_id: str = "", report_path: str = "", destination: str = "local_outbox") -> dict[str, Any]:
    _sync_state_root()
    if destination != "local_outbox":
        raise SupportError("Only destination=local_outbox is currently supported by the local MCP server.")
    if report_path:
        source = Path(report_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise SupportError(f"report_path does not exist: {source}")
        try:
            report = json.loads(source.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise SupportError(f"report_path is not valid JSON: {source}") from exc
        if not isinstance(report, dict):
            raise SupportError("report_path must contain a JSON object.")
    else:
        if not incident_id:
            raise SupportError("incident_id or report_path is required.")
        built = build_bug_report(incident_id=incident_id)
        source = Path(built["report_path"])
        report = built["report"]
    outbox = outbox_dir()
    outbox_path = (outbox / f"{_queued_report_stem(report.get('report_id') or source.stem)}.queued.json").resolve()
    _ensure_within_outbox(outbox_path, outbox)
    ensure_path_budget(outbox_path, "support queued report path")
    shutil.copy2(source, outbox_path)
    append_jsonl(outbox / "submission_log.jsonl", {"submitted_at": now(), "destination": destination, "report_id": str(report.get("report_id") or ""), "incident_id": str(report.get("incident", {}).get("incident_id") or incident_id), "queued_path": str(outbox_path)})
    return {"status": "queued", "destination": destination, "queued_path": str(outbox_path), "message": "Bug report queued locally for the development crew. No network submission was attempted."}


def dismiss_incident(*, incident_id: str, reason: str = "") -> dict[str, Any]:
    _sync_state_root()
    incident_id = required_text(incident_id, "incident_id")
    append_jsonl(dismissed_path(), {"dismissed_at": now(), "incident_id": incident_id, "reason": str(reason or "").strip()})
    return {"status": "ok", "incident_id": incident_id, "dismissed": True}


def support_surface_value() -> dict[str, Any]:
    summary = list_incidents(limit=5)
    assessments = load_assessments()
    return {"support_state_root": summary["support_state_root"], "event_count": summary["event_count"], "assessment_count": len(assessments), "active_incident_count": summary["incident_count"], "dismissed_count": summary["dismissed_count"], "recent_incidents": summary["incidents"], "operation_links": []}


def support_summary_value() -> dict[str, Any]:
    _sync_state_root()
    events = load_events()
    assessments = load_assessments()
    dismissed = load_dismissed()
    active_incidents = incidents_from_events(events, dismissed=dismissed)
    return {
        "support_state_root": str(state_root()),
        "event_count": len(events),
        "assessment_count": len(assessments),
        "active_incident_count": len(active_incidents),
        "dismissed_count": len(dismissed),
    }


def _sync_state_root() -> None:
    _storage.state_root = state_root


def _queued_report_stem(value: object) -> str:
    raw = str(value or "").strip()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
    if not safe:
        safe = "support_report"
    if len(safe) <= _QUEUED_REPORT_STEM_MAX_CHARS:
        return safe
    digest = hash_text(raw)[:12]
    prefix = safe[: _QUEUED_REPORT_STEM_MAX_CHARS - len(digest) - 1].rstrip("._-")
    return f"{prefix or 'support_report'}-{digest}"


def _ensure_within_outbox(path: Path, outbox: Path) -> None:
    try:
        path.relative_to(outbox.resolve())
    except ValueError as exc:
        raise SupportError("support queued report path must stay inside the support outbox.") from exc


__all__ = [name for name in globals() if not name.startswith("_")]
