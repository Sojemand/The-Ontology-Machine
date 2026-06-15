"""Payload builders for OpenAI-compatible Chat Completions providers."""
from __future__ import annotations

from typing import Any

from .base import ProviderError
from .payload import schema_supports_strict


def message_to_chat(message: dict[str, Any]) -> dict[str, Any]:
    content = message.get("content", "")
    if isinstance(content, str):
        return {"role": message.get("role", "user"), "content": content}
    raise ProviderError("Ungueltiges Nachrichtenformat fuer Chat Provider")


def build_payload(
    model: str,
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    max_output_tokens: int,
    thinking_effort: str,
) -> dict[str, Any]:
    del thinking_effort
    payload: dict[str, Any] = {
        "model": model,
        "messages": [message_to_chat(message) for message in messages],
        "max_tokens": max_output_tokens,
    }
    if schema and schema_supports_strict(schema):
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "normalized_output",
                "schema": schema,
                "strict": True,
            },
        }
    else:
        payload["response_format"] = {"type": "json_object"}
    return payload


def payload_bytes(payload: dict[str, Any]) -> int | None:
    from .payload import payload_bytes as _payload_bytes

    return _payload_bytes(payload)
