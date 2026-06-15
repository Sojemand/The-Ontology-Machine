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


def parse_response(response_text: str, *, fallback_model: str) -> ParsedResponse:
    try:
        result = json.loads(response_text)
    except ValueError as exc:
        raise ProviderError("Chat Completions API lieferte ungueltiges JSON") from exc
    if not isinstance(result, dict):
        raise ProviderError("Chat Completions API lieferte ein ungueltiges Antwortobjekt")
    choices = result.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise ProviderError("Chat Completions API lieferte keine Antwortauswahl")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "")
    if isinstance(content, str) and content.strip():
        output_text = content
    elif isinstance(content, list):
        output_text = "".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict) and part.get("text")
        )
    else:
        output_text = ""
    if not output_text.strip():
        raise ProviderError("Chat Completions API lieferte keinen Text-Output")
    return ParsedResponse(
        output_text=output_text,
        usage=result.get("usage", {}),
        model=str(result.get("model", fallback_model) or fallback_model),
        response_id=str(result.get("id", "") or ""),
    )
