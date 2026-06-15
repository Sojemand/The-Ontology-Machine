from __future__ import annotations

SCHEMA_VERSION = 1
SUPPORT_DIR_NAME = "support"
EVENTS_NAME = "support_events.jsonl"
ASSESSMENTS_NAME = "incident_assessments.jsonl"
DISMISSED_NAME = "dismissed_incidents.jsonl"
OUTBOX_DIR_NAME = "outbox"
REPORTS_DIR_NAME = "bug_reports"


class SupportError(ValueError):
    """Raised when a support-monitor request is invalid."""


__all__ = [name for name in globals() if name.isupper() or name == "SupportError"]
