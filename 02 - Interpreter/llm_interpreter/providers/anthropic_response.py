"""Response parsing helpers for the Anthropic Messages API."""
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
        raise ProviderError("Anthropic Messages API lieferte ungueltiges JSON") from exc
    if not isinstance(result, dict):
        raise ProviderError("Anthropic Messages API lieferte ein ungueltiges Antwortobjekt")
    output_text = _extract_output_text(result)
    return ParsedResponse(
        output_text=output_text,
        usage=result.get("usage", {}),
        model=str(result.get("model", fallback_model) or fallback_model),
        response_id=str(result.get("id", "") or ""),
    )


def _extract_output_text(result: dict[str, Any]) -> str:
    texts: list[str] = []
    for block in result.get("content", []) or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and block.get("text"):
            texts.append(str(block["text"]))
    output_text = "".join(texts).strip()
    if not output_text:
        raise ProviderError("Anthropic Messages API lieferte keinen Text-Output")
    return output_text
