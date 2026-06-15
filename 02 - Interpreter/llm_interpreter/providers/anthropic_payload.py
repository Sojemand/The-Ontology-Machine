"""Payload builders for the Anthropic Messages API."""
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
    del thinking_effort
    system_lines: list[str] = []
    converted: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", "user")).strip().lower()
        if role == "system":
            system_lines.extend(_system_lines(message.get("content", "")))
            continue
        converted.append({"role": "assistant" if role == "assistant" else "user", "content": _content_blocks(message.get("content", ""))})
    payload: dict[str, Any] = {"model": model, "max_tokens": max_output_tokens, "messages": converted}
    if system_lines:
        payload["system"] = "\n\n".join(line for line in system_lines if line)
    if schema is not None:
        payload["output_config"] = {"format": {"type": "json_schema", "schema": dict(schema)}}
    return payload


def _system_lines(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content] if content.strip() else []
    if not isinstance(content, list):
        return []
    return [str(block.get("text", "")).strip() for block in content if isinstance(block, dict) and block.get("type") == "text"]


def _content_blocks(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if not isinstance(content, list):
        raise ProviderError("Ungueltiges Nachrichtenformat fuer Anthropic Provider")
    return [_message_block_to_content(block) for block in content or []]


def _message_block_to_content(block: Any) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise ProviderError("Ungueltiger Inhaltsblock fuer Anthropic Provider")
    if block.get("type") == "text":
        return {"type": "text", "text": block.get("text", "")}
    if block.get("type") != "input_image":
        raise ProviderError(f"Nicht unterstuetzter Inhaltsblock: {block.get('type')!r}")
    match = _DATA_URL.match(str(block.get("image_url", "")))
    if match is None:
        raise ProviderError("Anthropic Provider erwartet base64 data URLs fuer Bilder")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": match.group("mime"),
            "data": match.group("data"),
        },
    }
