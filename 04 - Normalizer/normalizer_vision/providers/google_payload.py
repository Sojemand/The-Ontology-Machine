"""Payload builders for the Google Gemini generateContent API."""
from __future__ import annotations

from typing import Any

from .payload import schema_supports_strict


def build_payload(model: str, messages: list[dict[str, Any]], schema: dict[str, Any] | None, max_output_tokens: int, thinking_effort: str) -> dict[str, Any]:
    del model, thinking_effort
    payload: dict[str, Any] = {
        "contents": [
            {"role": "model" if str(message.get("role", "")).strip().lower() == "assistant" else "user", "parts": [{"text": str(message.get("content", ""))}]}
            for message in messages
            if str(message.get("role", "")).strip().lower() != "system"
        ],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }
    system = "\n\n".join(str(message.get("content", "")).strip() for message in messages if str(message.get("role", "")).strip().lower() == "system" and str(message.get("content", "")).strip())
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if schema and schema_supports_strict(schema):
        payload["generationConfig"]["responseJsonSchema"] = schema
    return payload
