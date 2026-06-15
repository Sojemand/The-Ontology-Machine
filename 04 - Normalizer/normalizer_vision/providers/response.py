"""Response parsing for the Normalizer OpenAI provider."""
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
        raise ProviderError("OpenAI Responses API lieferte ungueltiges JSON") from exc
    if not isinstance(result, dict):
        raise ProviderError("OpenAI Responses API lieferte ein ungueltiges Antwortobjekt")
    usage = result.get("usage", {})
    output_text = extract_output_text(result)
    output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
    return ParsedResponse(
        output_text=output_text,
        usage=usage,
        model=str(result.get("model", fallback_model) or fallback_model),
        response_id=str(result.get("id", "") or ""),
        output_tokens=output_tokens,
        incomplete_reason=incomplete_reason(result),
        json_is_valid=is_valid_json_object_text(output_text) if output_text else False,
    )


def extract_output_text(result: dict[str, Any]) -> str:
    output_text = result.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    for item in result.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for block in item.get("content", []) or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") in ("output_text", "text") and block.get("text"):
                return str(block["text"])
    return ""


def incomplete_reason(result: dict[str, Any]) -> str | None:
    details = result.get("incomplete_details")
    if isinstance(details, dict) and details.get("reason") is not None:
        return str(details.get("reason"))
    status = result.get("status")
    if isinstance(status, str) and status.strip().lower() == "incomplete":
        return "incomplete"
    return None


def is_valid_json_object_text(text: str) -> bool:
    if not text.strip():
        return False
    try:
        payload = json.loads(text)
    except ValueError:
        return False
    return isinstance(payload, dict)
