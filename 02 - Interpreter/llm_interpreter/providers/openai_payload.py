"""Payload builders for the OpenAI Responses API provider."""
from __future__ import annotations

from typing import Any

from ..models.types import VISION_IMAGE_DETAIL
from .base import ProviderError

_STRUCTURED_OUTPUT_NAME = "kernel_llm_output"


def text_format_for_schema(schema: dict[str, Any] | None) -> dict[str, Any]:
    if schema is None:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "name": _STRUCTURED_OUTPUT_NAME,
        "strict": True,
        "schema": dict(schema),
    }


def message_to_input(message: dict[str, Any]) -> dict[str, Any]:
    content = message.get("content", "")
    if isinstance(content, str):
        blocks = [{"type": "input_text", "text": content}]
    elif not isinstance(content, list):
        raise ProviderError("Ungueltiges Nachrichtenformat fuer OpenAI Provider")
    else:
        blocks = [_message_block_to_input(block) for block in content or []]
    return {"role": message.get("role", "user"), "content": blocks}


def build_payload(
    model: str,
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    max_output_tokens: int,
    thinking_effort: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "input": [message_to_input(message) for message in messages],
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": thinking_effort},
        "text": {"format": text_format_for_schema(schema)},
    }


def _message_block_to_input(block: Any) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise ProviderError("Ungueltiger Inhaltsblock fuer OpenAI Provider")
    if block.get("type") == "text":
        return {"type": "input_text", "text": block.get("text", "")}
    if block.get("type") == "input_image":
        return {
            "type": "input_image",
            "image_url": block.get("image_url", ""),
            "detail": block.get("detail", VISION_IMAGE_DETAIL),
        }
    raise ProviderError(f"Nicht unterstuetzter Inhaltsblock: {block.get('type')!r}")
