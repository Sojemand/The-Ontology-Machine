from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import socket
from typing import Any
import urllib.error
import urllib.request

from .errors import LlmOcrConfigurationError, LlmOcrResponseError
from .prompting import responses_content_parts
from .provider_http import sanitize_provider_error
from .request_capture import persist_request
from .settings import RESPONSES_FAMILIES, LlmOcrSettings

_DEFAULT_OAUTH_INSTRUCTIONS = "Return valid json only. Return the requested payload exactly. No prose."
_DEFAULT_OAUTH_REASONING_EFFORT = "none"
_OAUTH_BACKEND_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
_OAUTH_BACKEND_ORIGINATOR = "codex_cli_rs"
_OAUTH_BACKEND_USER_AGENT = "codex-cli/0.108.0-alpha.12"


@dataclass(frozen=True)
class _SseEvent:
    event: str
    data: dict[str, Any]


def call_oauth_backend(settings: LlmOcrSettings, assets: list[dict[str, str]], *, source_path: str | Path | None, request_oauth_backend=None) -> str:
    if settings.provider_id.strip().lower() != "openai" or settings.provider_family not in RESPONSES_FAMILIES:
        raise LlmOcrConfigurationError("optimizer_ocr OAuth ist nur fuer OpenAI Responses-Provider unterstuetzt.")
    request_backend = request_oauth_backend or request_oauth_backend_default
    payload = {
        "model": settings.model,
        "instructions": _DEFAULT_OAUTH_INSTRUCTIONS,
        "input": [{"role": "user", "content": ensure_json_input_hint(responses_content_parts(assets, source_path=source_path), {"type": "json_object"})}],
        "reasoning": {"effort": _DEFAULT_OAUTH_REASONING_EFFORT},
        "stream": True,
        "text": {"format": {"type": "json_object"}},
        "tool_choice": "auto",
        "parallel_tool_calls": True,
        "store": False,
    }
    persist_request(
        settings,
        assets,
        source_path=source_path,
        endpoint=_OAUTH_BACKEND_RESPONSES_URL,
        provider_payload=payload,
        provider_route="oauth_backend",
    )
    status_code, raw_text = request_backend(
        access_token=settings.oauth_access_token,
        account_id=settings.oauth_account_id,
        payload=payload,
        timeout=settings.timeout_seconds,
    )
    if status_code >= 400:
        raise LlmOcrResponseError(f"LLM-OCR OAuth Backend Fehler {status_code}: {sanitize_provider_error(raw_text)}")
    events = decode_sse_events(raw_text)
    error_message = oauth_event_error(events)
    if error_message:
        raise LlmOcrResponseError(f"LLM-OCR OAuth Backend Fehler {status_code}: {error_message}")
    completed = completed_oauth_response(events)
    output_text = oauth_output_text(events, completed)
    if completed is None or not output_text:
        raise LlmOcrResponseError("LLM-OCR OAuth Backend lieferte keinen Text-Output.")
    return output_text


def request_oauth_backend_default(*, access_token: str, account_id: str, payload: dict[str, Any], timeout: int) -> tuple[int, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "originator": _OAUTH_BACKEND_ORIGINATOR,
        "User-Agent": _OAUTH_BACKEND_USER_AGENT,
    }
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id
    request = urllib.request.Request(_OAUTH_BACKEND_RESPONSES_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.getcode()), response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except socket.timeout as exc:
        raise LlmOcrResponseError(f"LLM-OCR OAuth Backend Timeout nach {timeout}s") from exc
    except urllib.error.URLError as exc:
        raise LlmOcrResponseError(f"LLM-OCR OAuth Backend nicht erreichbar: {exc.reason}") from exc
    except OSError as exc:
        raise LlmOcrResponseError(f"LLM-OCR OAuth Backend Anfrage fehlgeschlagen: {exc}") from exc


def decode_sse_events(raw_text: str) -> list[_SseEvent]:
    events: list[_SseEvent] = []
    event_name = "message"
    data_lines: list[str] = []
    for line in raw_text.splitlines():
        text = line.rstrip("\r")
        if not text:
            flush_sse_event(events, event_name, data_lines)
            event_name = "message"
            data_lines = []
        elif not text.startswith(":") and text.startswith("event:"):
            event_name = text.partition(":")[2].strip() or "message"
        elif not text.startswith(":") and text.startswith("data:"):
            data_lines.append(text.partition(":")[2].lstrip())
    flush_sse_event(events, event_name, data_lines)
    return events


def flush_sse_event(events: list[_SseEvent], event_name: str, data_lines: list[str]) -> None:
    if not data_lines:
        return
    try:
        payload = json.loads("\n".join(data_lines))
    except json.JSONDecodeError as exc:
        raise LlmOcrResponseError(f"Ungueltige SSE-Antwort fuer {event_name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LlmOcrResponseError(f"SSE-Payload fuer {event_name} ist kein JSON-Objekt")
    events.append(_SseEvent(event=event_name, data=payload))


def oauth_event_error(events: list[_SseEvent]) -> str:
    for event in events:
        if event.event == "error":
            return sanitize_provider_error(str(event.data.get("message") or event.data.get("error") or "backend stream error"))
    return ""


def completed_oauth_response(events: list[_SseEvent]) -> dict[str, Any] | None:
    for event in reversed(events):
        if event.event == "response.completed":
            value = event.data.get("response")
            return value if isinstance(value, dict) else {}
    return None


def oauth_output_text(events: list[_SseEvent], completed: dict[str, Any] | None) -> str:
    for event in reversed(events):
        if event.event == "response.output_text.done":
            return str(event.data.get("text") or "")
    if completed is None or not isinstance(completed.get("output"), list):
        return ""
    for item in completed["output"]:
        content = item.get("content") if isinstance(item, dict) else None
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text" and part.get("text"):
                    return str(part["text"])
    return ""


def ensure_json_input_hint(content_parts: list[dict[str, Any]], text_format: dict[str, Any]) -> list[dict[str, Any]]:
    if text_format.get("type") != "json_object":
        return list(content_parts)
    for part in content_parts:
        if part.get("type") == "input_text" and "json" in str(part.get("text", "")).lower():
            return list(content_parts)
    return [{"type": "input_text", "text": "Return valid JSON only."}, *content_parts]
