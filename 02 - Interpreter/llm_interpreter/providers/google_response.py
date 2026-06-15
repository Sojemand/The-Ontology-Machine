"""Response parsing helpers for the Google Gemini generateContent API."""
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
        raise ProviderError("Google Gemini API lieferte ungueltiges JSON") from exc
    if not isinstance(result, dict):
        raise ProviderError("Google Gemini API lieferte ein ungueltiges Antwortobjekt")
    candidates = result.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        raise ProviderError("Google Gemini API lieferte keine Kandidaten")
    content = candidates[0].get("content", {}) if isinstance(candidates[0], dict) else {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    output_text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict) and part.get("text")).strip()
    if not output_text:
        raise ProviderError("Google Gemini API lieferte keinen Text-Output")
    usage = result.get("usageMetadata", {})
    return ParsedResponse(
        output_text=output_text,
        usage={
            "input_tokens": usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        },
        model=fallback_model,
        response_id=str(result.get("responseId", "") or ""),
    )
