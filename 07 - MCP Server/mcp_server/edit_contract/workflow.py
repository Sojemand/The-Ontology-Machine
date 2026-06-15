"""Workflow helpers for MCP Server edit-contract actions."""

from __future__ import annotations

from pathlib import Path

from ..atomic_io import atomic_json_write
from .. import support_monitor
from .describe_surfaces import describe_surfaces
from .read_surface import read_surface
from .summary_cards import build_summary_cards
from .summary_text import build_module_summary
from .validate_surface import validate_surface
from .write_surface import write_surface


def error_response(message: str) -> dict:
    return {"status": "error", "reason": str(message)}


def describe(*, module_root) -> dict:
    return {
        "status": "ok",
        "surfaces": describe_surfaces(module_root=module_root),
        "module_summary": build_module_summary(),
        "summary_cards": build_summary_cards(module_root=module_root),
    }


def read_bundle(*, module_root) -> dict:
    described = describe(module_root=module_root)
    return _bundle_response(described, lambda surface_id: read_surface(surface_id, module_root=module_root))


def read(surface_id: str, *, module_root) -> dict:
    return {"status": "ok", "surface_id": surface_id, "value": read_surface(surface_id, module_root=module_root)}


def validate(surface_id: str, value: dict, *, module_root) -> dict:
    return {
        "status": "ok",
        "surface_id": surface_id,
        "value": validate_surface(surface_id, value, module_root=module_root),
    }


def write(surface_id: str, value: dict, *, module_root) -> dict:
    validate_surface(surface_id, value, module_root=module_root)
    return {"status": "ok", "surface_id": surface_id, "value": write_surface(surface_id, value, module_root=module_root)}


def run_support_action(action: str, payload: dict, *, module_root) -> dict:
    del module_root
    if action == "assess_support_incident":
        return support_monitor.assess_incident(payload)
    if action == "list_support_incidents":
        return support_monitor.list_incidents(
            include_dismissed=_bool(payload.get("show_dismissed"), default=False, field="show_dismissed"),
            limit=_positive_int(payload.get("limit", 20), field="limit"),
        )
    if action == "preview_support_bug_report":
        assessment = support_monitor.require_reportable_assessment(payload.get("assessment_id"))
        result = support_monitor.preview_bug_report(
            incident_id=str(assessment["incident_id"]),
            user_note=str(payload.get("user_note") or ""),
            include_recent_events=_bool(payload.get("with_recent_events"), default=True, field="with_recent_events"),
        )
        result["report"]["support_assessment"] = assessment
        result["assessment"] = assessment
        return result
    if action == "build_support_bug_report":
        assessment = support_monitor.require_reportable_assessment(payload.get("assessment_id"))
        result = support_monitor.build_bug_report(
            incident_id=str(assessment["incident_id"]),
            user_note=str(payload.get("user_note") or ""),
            include_recent_events=_bool(payload.get("with_recent_events"), default=True, field="with_recent_events"),
            output_path=str(payload.get("output_path") or ""),
        )
        result["report"]["support_assessment"] = assessment
        atomic_json_write(Path(result["report_path"]), result["report"], indent=2, trailing_newline=True)
        result["assessment"] = assessment
        return result
    if action == "queue_support_bug_report":
        assessment = support_monitor.require_reportable_assessment(payload.get("assessment_id"))
        if not _bool(payload.get("user_confirmed"), default=False, field="user_confirmed"):
            raise ValueError("user_confirmed=true is required before queueing a local support report.")
        report_path = _required_text(payload.get("report_path"), field="report_path")
        return support_monitor.submit_bug_report(
            incident_id=str(assessment["incident_id"]),
            report_path=report_path,
            destination=str(payload.get("destination") or "local_outbox"),
        )
    if action == "dismiss_support_incident":
        return support_monitor.dismiss_incident(
            incident_id=_required_text(payload.get("incident_id"), field="incident_id"),
            reason=str(payload.get("reason") or ""),
        )
    return error_response(f"Unbekannte Support-Aktion: {action}")


def _bundle_response(described: dict, reader) -> dict:
    if described.get("status") != "ok":
        return described
    return {
        "status": "ok",
        "module_summary": described.get("module_summary", ""),
        "summary_cards": described.get("summary_cards", []),
        "surfaces": _bundle_surfaces(described.get("surfaces", ()), reader),
    }


def _bundle_surfaces(descriptors, reader) -> list[dict]:
    surfaces = []
    for descriptor in descriptors:
        item = dict(descriptor)
        try:
            item["value"] = reader(str(item.get("surface_id") or ""))
        except Exception as exc:
            item["load_error"] = str(exc)
        surfaces.append(item)
    return surfaces


def _required_text(value: object, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} fehlt oder ist ungueltig.")
    return text


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} muss eine positive Ganzzahl sein.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} muss eine positive Ganzzahl sein.") from None
    if parsed < 1:
        raise ValueError(f"{field} muss eine positive Ganzzahl sein.")
    return parsed


def _bool(value: object, *, default: bool, field: str) -> bool:
    if value is None or value == "":
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field} muss true oder false sein.")
    return value
