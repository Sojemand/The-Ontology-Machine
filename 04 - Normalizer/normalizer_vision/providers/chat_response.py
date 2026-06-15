"""Response parsing helpers for OpenAI-compatible Chat Completions providers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .base import ProviderError


@dataclass(frozen=True)
class ParsedResponse:
    output_text: str
    usage: dict[str, Any]
    model: str
    response_id: str
    output_tokens: int
    incomplete_reason: str | None
    json_is_valid: bool


def parse_response(response: Any, *, fallback_model: str) -> ParsedResponse:
    try:
        result = response.json()
    except ValueError as exc:
        raise ProviderError("Chat Completions API lieferte ungueltiges JSON") from exc
    if not isinstance(result, dict):
        raise ProviderError("Chat Completions API lieferte ein ungueltiges Antwortobjekt")
    choices = result.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise ProviderError("Chat Completions API lieferte keine Antwortauswahl")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message", {}) if isinstance(first, dict) else {}
    content = message.get("content", "")
    output_text = str(content) if isinstance(content, str) else ""
    usage = result.get("usage", {})
    return ParsedResponse(
        output_text=output_text,
        usage=usage,
        model=str(result.get("model", fallback_model) or fallback_model),
        response_id=str(result.get("id", "") or ""),
        output_tokens=int(usage.get("completion_tokens", 0) or 0),
        incomplete_reason="max_tokens" if str(first.get("finish_reason", "")).strip().lower() == "length" else None,
        json_is_valid=is_valid_json_object_text(output_text) if output_text else False,
    )


def is_valid_json_object_text(text: str) -> bool:
    if not text.strip():
        return False
    try:
        payload = json.loads(text)
    except ValueError:
        return False
    return isinstance(payload, dict)
