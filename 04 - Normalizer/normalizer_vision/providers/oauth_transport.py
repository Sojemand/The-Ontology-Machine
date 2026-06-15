"""Direct ChatGPT Codex backend transport for orchestrated OAuth runs."""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .base import ProviderError
from .oauth_sse import (
    SseEvent,
    completed_response,
    decode_sse_events,
    dict_value,
    event_error,
    output_text,
)

BACKEND_BASE_URL = "https://chatgpt.com/backend-api/codex"
RESPONSES_URL = f"{BACKEND_BASE_URL}/responses"
DEFAULT_ORIGINATOR = "codex_cli_rs"
DEFAULT_USER_AGENT = "codex-cli/0.108.0-alpha.12"


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
            "stream": True,
            "text": {"format": text_format},
            "reasoning": {"effort": reasoning_effort},
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "store": False,
        },
        timeout=timeout,
    )
    if status_code >= 400:
        return TransportResult(success=False, status_code=status_code, error=raw_text[:500] or f"http {status_code}")
    events = decode_sse_events(raw_text)
    error_message = event_error(events)
    if error_message:
        return TransportResult(success=False, status_code=status_code, event_count=len(events), error=error_message)
    completed = completed_response(events)
    output = output_text(events, completed)
    if completed is None or not output:
        return TransportResult(
            success=False,
            status_code=status_code,
            event_count=len(events),
            error="response.completed fehlt oder enthaelt keinen Text-Output",
        )
    return TransportResult(
        success=True,
        status_code=status_code,
        output_text=output,
        response_id=str(completed.get("id") or ""),
        usage=dict_value(completed.get("usage")),
        event_count=len(events),
    )


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


def _ensure_json_input_hint(content_parts: list[dict[str, Any]], text_format: dict[str, Any]) -> list[dict[str, Any]]:
    if text_format.get("type") != "json_object":
        return list(content_parts)
    for part in content_parts:
        if part.get("type") == "input_text" and "json" in str(part.get("text", "")).lower():
            return list(content_parts)
    return [{"type": "input_text", "text": "Return valid JSON only."}, *content_parts]
