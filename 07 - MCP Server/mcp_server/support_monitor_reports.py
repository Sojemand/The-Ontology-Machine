from __future__ import annotations

from pathlib import Path
from typing import Any

from .support_monitor_events import incidents_from_events
from .support_monitor_redaction import hash_text, redact_text
from .support_monitor_storage import load_events, load_json_file, now
from .support_monitor_types import SCHEMA_VERSION, SupportError


def build_report(incident_id: str, *, user_note: str, include_recent_events: bool) -> dict[str, Any]:
    incident_id = str(incident_id or "").strip()
    if not incident_id:
        raise SupportError("incident_id is required.")
    events = load_events()
    incidents = incidents_from_events(events, dismissed=set())
    incident = next((item for item in incidents if item.get("incident_id") == incident_id), None)
    if incident is None:
        raise SupportError(f"Unknown incident_id: {incident_id}")
    related_signature = str(incident.get("signature") or "")
    related_events = [item for item in events if str(item.get("signature") or "") == related_signature]
    report_id = hash_text(f"{incident_id}|{now()}")[:16]
    return {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "created_at": now(),
        "source": "vision_pipeline_mcp_support_monitor",
        "privacy_note": "Report content is redacted by key-name and API-key pattern. Raw documents, database dumps, and plaintext secrets are not included by this local support workflow.",
        "incident": incident,
        "user_note": redact_text(str(user_note or "")),
        "runtime_context": runtime_context(),
        "recent_events": related_events[-10:] if include_recent_events else [],
        "developer_next_steps": [
            "Reproduce in a source workspace, not inside the installed runtime.",
            "Map the failing module/action to the owning source package.",
            "Add or update a regression test before shipping a new runtime or installer build.",
            "Do not ask the installed MCP server to patch product code in place.",
        ],
    }


def runtime_context() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    return {
        "module_root": str(root),
        "module_manifest": load_json_file(root / "module-manifest.json"),
        "runtime_manifest": load_json_file(root / "runtime" / "runtime-manifest.json"),
        "policy_path": str(root / "config" / "agent_permissions.json"),
    }


__all__ = ["build_report", "runtime_context"]
