"""Structured response envelopes for Edit-Suite-facing actions."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def build_result(
    *,
    headline: str,
    summary_lines: list[str] | tuple[str, ...],
    detail,
    artifacts: list[dict] | None = None,
    table: dict | None = None,
    status: str = "ok",
) -> dict:
    payload = {
        "status": status,
        "headline": headline,
        "summary_lines": [str(line) for line in summary_lines if str(line).strip()],
        "artifacts": _json_safe(list(artifacts or [])),
        "detail": _json_safe(detail),
    }
    if table:
        payload["table"] = _json_safe(table)
    return payload


def kv_artifacts(items: list[tuple[str, object]]) -> list[dict]:
    return [{"label": label, "value": "" if value is None else str(value)} for label, value in items if str(label).strip()]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(child) for child in value]
    if isinstance(value, set):
        return sorted(_json_safe(child) for child in value)
    if isinstance(value, Path):
        return str(value)
    return value
