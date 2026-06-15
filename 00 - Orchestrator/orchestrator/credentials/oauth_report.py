"""Sanitized OAuth session reports for the Orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..state import atomic_json_write


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def write_oauth_report(state_dir: Path, report: dict[str, Any]) -> Path:
    target = Path(state_dir) / "oauth_latest_report.json"
    atomic_json_write(target, sanitize_report(report))
    return target


def sanitize_report(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in {"access_token", "refresh_token", "authorization_code", "code", "id_token"}:
                output[key] = "[REDACTED]"
                continue
            output[key] = sanitize_report(child)
        return output
    if isinstance(value, list):
        return [sanitize_report(item) for item in value]
    return value
