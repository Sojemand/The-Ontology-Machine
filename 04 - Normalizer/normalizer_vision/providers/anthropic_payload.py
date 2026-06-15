"""Payload builders for the Anthropic Messages API."""
from __future__ import annotations

from typing import Any

from .payload import schema_supports_strict

_TOOL_NAME = "emit_structured_output"


def build_payload(model: str, messages: list[dict[str, Any]], schema: dict[str, Any] | None, max_output_tokens: int, thinking_effort: str) -> dict[str, Any]:
    del thinking_effort
    system = "\n\n".join(str(message.get("content", "")).strip() for message in messages if str(message.get("role", "")).strip().lower() == "system" and str(message.get("content", "")).strip())
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_output_tokens,
        "messages": [
            {"role": "assistant" if str(message.get("role", "")).strip().lower() == "assistant" else "user", "content": [{"type": "text", "text": str(message.get("content", ""))}]}
            for message in messages
            if str(message.get("role", "")).strip().lower() != "system"
        ],
    }
    if system:
        payload["system"] = system
    if schema and schema_supports_strict(schema):
        payload["tools"] = [{"name": _TOOL_NAME, "description": "Return the final JSON payload.", "input_schema": schema}]
        payload["tool_choice"] = {"type": "tool", "name": _TOOL_NAME}
    return payload
