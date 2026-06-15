from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .base import ProviderError


@dataclass(frozen=True, slots=True)
class SseEvent:
    event: str
    data: dict[str, Any]


def decode_sse_events(raw_text: str) -> list[SseEvent]:
    events: list[SseEvent] = []
    event_name = "message"
    data_lines: list[str] = []
    for line in raw_text.splitlines():
        text = line.rstrip("\r")
        if not text:
            _flush_event(events, event_name, data_lines)
            event_name = "message"
            data_lines = []
            continue
        if text.startswith(":"):
            continue
        if text.startswith("event:"):
            event_name = text.partition(":")[2].strip() or "message"
            continue
        if text.startswith("data:"):
            data_lines.append(text.partition(":")[2].lstrip())
    _flush_event(events, event_name, data_lines)
    return events


def event_error(events: list[SseEvent]) -> str:
    for event in events:
        if event.event == "error":
            return str(event.data.get("message") or event.data.get("error") or "backend stream error")
    return ""


def completed_response(events: list[SseEvent]) -> dict[str, Any] | None:
    for event in reversed(events):
        if event.event == "response.completed":
            return dict_value(event.data.get("response"))
    return None


def output_text(events: list[SseEvent], completed: dict[str, Any] | None) -> str:
    for event in reversed(events):
        if event.event == "response.output_text.done":
            return str(event.data.get("text") or "")
    if completed is None:
        return ""
    output = completed.get("output")
    if not isinstance(output, list):
        return ""
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text" and part.get("text"):
                return str(part["text"])
    return ""


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _flush_event(events: list[SseEvent], event_name: str, data_lines: list[str]) -> None:
    if not data_lines:
        return
    raw_data = "\n".join(data_lines)
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Ungueltige SSE-Antwort fuer {event_name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProviderError(f"SSE-Payload fuer {event_name} ist kein JSON-Objekt")
    events.append(SseEvent(event=event_name, data=payload))
