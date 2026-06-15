from __future__ import annotations

from typing import Any

from .support_monitor_redaction import hash_text, highest_severity, message_fingerprint, redact, redact_text, stacktrace_excerpt
from .support_monitor_storage import now, required_text
from .support_monitor_types import SCHEMA_VERSION, SupportError


def normalize_event(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SupportError("support event payload must be a JSON object.")
    timestamp = str(payload.get("timestamp") or now())
    module_key = required_text(payload.get("module_key"), "module_key")
    action = str(payload.get("action") or "").strip()
    severity = str(payload.get("severity") or "error").strip().lower()
    if severity not in {"info", "warning", "error", "critical"}:
        raise SupportError("severity must be one of: info, warning, error, critical")
    status = str(payload.get("status") or "error").strip() or "error"
    message = redact_text(str(payload.get("message") or ""))
    exception_type = str(payload.get("exception_type") or "").strip()
    stacktrace = redact_text(str(payload.get("stacktrace") or ""))
    metadata = redact(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
    artifact_refs = redact(payload.get("artifact_refs") if isinstance(payload.get("artifact_refs"), list) else [])
    signature = _signature({"module_key": module_key, "action": action, "status": status, "message": message_fingerprint(message), "exception_type": exception_type, "stacktrace_hash": hash_text(stacktrace) if stacktrace else ""})
    event_id = hash_text(f"{timestamp}|{signature}|{message}")[:16]
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "timestamp": timestamp,
        "module_key": module_key,
        "action": action,
        "severity": severity,
        "status": status,
        "message": message,
        "exception_type": exception_type,
        "stacktrace_hash": hash_text(stacktrace) if stacktrace else "",
        "stacktrace_excerpt": stacktrace_excerpt(stacktrace),
        "signature": signature,
        "redaction_class": str(payload.get("redaction_class") or "support_safe").strip() or "support_safe",
        "artifact_refs": artifact_refs,
        "metadata": metadata,
    }


def incidents_from_events(events: list[dict[str, Any]], *, dismissed: set[str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        signature = str(event.get("signature") or "").strip()
        if signature:
            grouped.setdefault(signature, []).append(event)
    incidents = []
    for signature, items in grouped.items():
        items.sort(key=lambda item: str(item.get("timestamp") or ""))
        incident_id = hash_text(signature)[:12]
        if incident_id in dismissed:
            continue
        sample = items[-1]
        incidents.append({
            "incident_id": incident_id,
            "signature": signature,
            "severity": highest_severity([str(item.get("severity") or "error") for item in items]),
            "module_key": str(sample.get("module_key") or ""),
            "action": str(sample.get("action") or ""),
            "status": str(sample.get("status") or ""),
            "message": str(sample.get("message") or ""),
            "exception_type": str(sample.get("exception_type") or ""),
            "first_seen": str(items[0].get("timestamp") or ""),
            "last_seen": str(sample.get("timestamp") or ""),
            "event_count": len(items),
            "sample_event_ids": [str(item.get("event_id") or "") for item in items[-5:]],
        })
    return incidents


def _signature(payload: dict[str, str]) -> str:
    return "|".join(f"{key}={value}" for key, value in sorted(payload.items()))


__all__ = ["normalize_event", "incidents_from_events"]
