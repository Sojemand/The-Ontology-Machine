"""Payload builders for the Google Gemini generateContent API."""
from __future__ import annotations

import re
from typing import Any

from .base import ProviderError

_DATA_URL = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.IGNORECASE)


def build_payload(
    model: str,
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    max_output_tokens: int,
    thinking_effort: str,
) -> dict[str, Any]:
    del model, thinking_effort
    payload: dict[str, Any] = {
        "contents": [_message_to_content(message) for message in messages if str(message.get("role", "")).strip().lower() != "system"],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }
    if schema is not None:
        payload["generationConfig"]["responseJsonSchema"] = dict(schema)
    system_text = "\n\n".join(_system_lines(messages))
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}
    return payload


def _system_lines(messages: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for message in messages:
        if str(message.get("role", "")).strip().lower() != "system":
            continue
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            lines.append(content.strip())
    return lines


def _message_to_content(message: dict[str, Any]) -> dict[str, Any]:
    role = str(message.get("role", "user")).strip().lower()
    content = message.get("content", "")
    if isinstance(content, str):
        parts = [{"text": content}]
    elif isinstance(content, list):
        parts = [_message_block_to_part(block) for block in content or []]
    else:
        raise ProviderError("Ungueltiges Nachrichtenformat fuer Google Provider")
    return {"role": "model" if role == "assistant" else "user", "parts": parts}


def _message_block_to_part(block: Any) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise ProviderError("Ungueltiger Inhaltsblock fuer Google Provider")
    if block.get("type") == "text":
        return {"text": block.get("text", "")}
    if block.get("type") != "input_image":
        raise ProviderError(f"Nicht unterstuetzter Inhaltsblock: {block.get('type')!r}")
    match = _DATA_URL.match(str(block.get("image_url", "")))
    if match is None:
        raise ProviderError("Google Provider erwartet base64 data URLs fuer Bilder")
    return {"inlineData": {"mimeType": match.group("mime"), "data": match.group("data")}}
