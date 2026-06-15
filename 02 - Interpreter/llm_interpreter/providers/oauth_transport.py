"""Direct ChatGPT Codex backend transport for orchestrated OAuth runs."""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .base import ProviderError, sanitize_error_text

BACKEND_BASE_URL = "https://chatgpt.com/backend-api/codex"
RESPONSES_URL = f"{BACKEND_BASE_URL}/responses"
DEFAULT_ORIGINATOR = "codex_cli_rs"
DEFAULT_USER_AGENT = "codex-cli/0.108.0-alpha.12"

@dataclass(frozen=True, slots=True)
class SseEvent:
    event: str
    data: dict[str, Any]

@dataclass(frozen=True, slots=True)
class TransportResult:
    success: bool
    status_code: int
    output_text: str = ""
    response_id: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    event_count: int = 0

def run_backend_content_response(
    *,
    access_token: str,
    account_id: str,
    model: str,
    content_parts: list[dict[str, Any]],
    text_format: dict[str, Any],
    instructions: str,
    max_output_tokens: int,
    reasoning_effort: str,
    timeout: int,
) -> TransportResult:
    payload_content_parts = _ensure_json_input_hint(content_parts, text_format)
    status_code, raw_text = _request_backend(
        access_token=access_token,
        account_id=account_id,
        payload={
            "model": model,
            "instructions": instructions,
            "input": [{"role": "user", "content": payload_content_parts}],
            "reasoning": {"effort": reasoning_effort},
            "stream": True,
            "text": {"format": text_format},
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "store": False,
        },
        timeout=timeout,
    )
    if status_code >= 400:
        return TransportResult(
            success=False,
            status_code=status_code,
            error=sanitize_error_text(raw_text) or f"http {status_code}",
        )
    events = decode_sse_events(raw_text)
    error_message = _event_error(events)
    if error_message:
        return TransportResult(success=False, status_code=status_code, event_count=len(events), error=error_message)
    completed = _completed_response(events)
    output_text = _output_text(events, completed)
    if completed is None or not output_text:
        return TransportResult(
            success=False,
            status_code=status_code,
            event_count=len(events),
            error="response.completed fehlt oder enthaelt keinen Text-Output",
        )
    return TransportResult(
        success=True,
        status_code=status_code,
        output_text=output_text,
        response_id=str(completed.get("id") or ""),
        usage=_dict_value(completed.get("usage")),
        event_count=len(events),
    )

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

def _request_backend(
    *,
    access_token: str,
    account_id: str,
    payload: dict[str, Any],
    timeout: int,
) -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "originator": DEFAULT_ORIGINATOR,
        "User-Agent": DEFAULT_USER_AGENT,
    }
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id
    request = urllib.request.Request(RESPONSES_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.getcode()), response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except socket.timeout as exc:
        raise ProviderError(f"OpenAI OAuth Backend Timeout nach {timeout}s") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"OpenAI OAuth Backend nicht erreichbar: {exc.reason}") from exc
    except OSError as exc:
        raise ProviderError(f"OpenAI OAuth Backend Anfrage fehlgeschlagen: {exc}") from exc

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


def _event_error(events: list[SseEvent]) -> str:
    for event in events:
        if event.event == "error":
            return sanitize_error_text(str(event.data.get("message") or event.data.get("error") or "backend stream error"))
    return ""


def _completed_response(events: list[SseEvent]) -> dict[str, Any] | None:
    for event in reversed(events):
        if event.event == "response.completed":
            return _dict_value(event.data.get("response"))
    return None


def _output_text(events: list[SseEvent], completed: dict[str, Any] | None) -> str:
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


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ensure_json_input_hint(content_parts: list[dict[str, Any]], text_format: dict[str, Any]) -> list[dict[str, Any]]:
    if text_format.get("type") != "json_object":
        return list(content_parts)
    for part in content_parts:
        if part.get("type") == "input_text" and "json" in str(part.get("text", "")).lower():
            return list(content_parts)
    return [{"type": "input_text", "text": "Return valid JSON only."}, *content_parts]
