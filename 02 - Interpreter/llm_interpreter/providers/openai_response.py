"""Response parsing helpers for the OpenAI Responses API provider."""
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
        raise ProviderError("OpenAI Responses API lieferte ungueltiges JSON") from exc
    if not isinstance(result, dict):
        raise ProviderError("OpenAI Responses API lieferte ein ungueltiges Antwortobjekt")
    return ParsedResponse(
        output_text=_extract_output_text(result),
        usage=result.get("usage", {}),
        model=str(result.get("model", fallback_model) or fallback_model),
        response_id=str(result.get("id", "") or ""),
    )


def _extract_output_text(result: dict[str, Any]) -> str:
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
                return block["text"]
    raise ProviderError("OpenAI Responses API lieferte keinen Text-Output")
