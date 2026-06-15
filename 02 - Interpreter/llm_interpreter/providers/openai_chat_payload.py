"""Payload builders for OpenAI-compatible Chat Completions providers."""
from __future__ import annotations

from typing import Any

from ..models.types import VISION_IMAGE_DETAIL
from .base import ProviderError

_STRUCTURED_OUTPUT_NAME = "kernel_llm_output"


def response_format_for_schema(schema: dict[str, Any] | None) -> dict[str, Any]:
    if schema is None:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": _STRUCTURED_OUTPUT_NAME,
            "strict": True,
            "schema": dict(schema),
        },
    }


def message_to_chat(message: dict[str, Any]) -> dict[str, Any]:
    content = message.get("content", "")
    if isinstance(content, str):
        return {"role": message.get("role", "user"), "content": content}
    if not isinstance(content, list):
        raise ProviderError("Ungueltiges Nachrichtenformat fuer Chat Provider")
    return {
        "role": message.get("role", "user"),
        "content": [_message_block_to_chat(block) for block in content or []],
    }


def build_payload(
    model: str,
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    max_output_tokens: int,
    thinking_effort: str,
) -> dict[str, Any]:
    del thinking_effort
    return {
        "model": model,
        "messages": [message_to_chat(message) for message in messages],
        "max_tokens": max_output_tokens,
        "response_format": response_format_for_schema(schema),
    }


def _message_block_to_chat(block: Any) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise ProviderError("Ungueltiger Inhaltsblock fuer Chat Provider")
    if block.get("type") == "text":
        return {"type": "text", "text": block.get("text", "")}
    if block.get("type") == "input_image":
        return {
            "type": "image_url",
            "image_url": {
                "url": block.get("image_url", ""),
                "detail": block.get("detail", VISION_IMAGE_DETAIL),
            },
        }
    raise ProviderError(f"Nicht unterstuetzter Inhaltsblock: {block.get('type')!r}")
