"""Response parsing helpers for the Google Gemini generateContent API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import ProviderError
from .response import is_valid_json_object_text


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
    result = response.json()
    if not isinstance(result, dict):
        raise ProviderError("Google Gemini API lieferte ein ungueltiges Antwortobjekt")
    candidates = result.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        raise ProviderError("Google Gemini API lieferte keine Kandidaten")
    first = candidates[0] if isinstance(candidates[0], dict) else {}
    content = first.get("content", {}) if isinstance(first, dict) else {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    output_text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict) and part.get("text"))
    usage = result.get("usageMetadata", {})
    return ParsedResponse(
        output_text=output_text,
        usage={"input_tokens": usage.get("promptTokenCount", 0), "output_tokens": usage.get("candidatesTokenCount", 0)},
        model=fallback_model,
        response_id=str(result.get("responseId", "") or ""),
        output_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
        incomplete_reason="max_tokens" if str(first.get("finishReason", "")).strip().upper() == "MAX_TOKENS" else None,
        json_is_valid=is_valid_json_object_text(output_text) if output_text else False,
    )
