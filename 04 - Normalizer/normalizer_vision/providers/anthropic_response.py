"""Response parsing helpers for the Anthropic Messages API."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .anthropic_payload import _TOOL_NAME
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
        raise ProviderError("Anthropic Messages API lieferte ein ungueltiges Antwortobjekt")
    output_text = ""
    for block in result.get("content", []) or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == _TOOL_NAME:
            output_text = json.dumps(block.get("input", {}), ensure_ascii=False, separators=(",", ":"))
            break
        if block.get("type") == "text" and block.get("text"):
            output_text += str(block["text"])
    usage = result.get("usage", {})
    return ParsedResponse(
        output_text=output_text,
        usage=usage,
        model=str(result.get("model", fallback_model) or fallback_model),
        response_id=str(result.get("id", "") or ""),
        output_tokens=int(usage.get("output_tokens", 0) or 0),
        incomplete_reason="max_tokens" if str(result.get("stop_reason", "")).strip().lower() == "max_tokens" else None,
        json_is_valid=is_valid_json_object_text(output_text) if output_text else False,
    )
