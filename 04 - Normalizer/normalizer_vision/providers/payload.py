"""Payload builders for the Normalizer OpenAI provider."""
from __future__ import annotations

import json
from typing import Any


def message_to_input(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": message.get("role", "user"),
        "content": [{"type": "input_text", "text": str(message.get("content", ""))}],
    }


def schema_supports_strict(schema: dict[str, Any] | None) -> bool:
    if not isinstance(schema, dict):
        return False
    schema_type = schema.get("type")
    if schema_type == "object" or (isinstance(schema_type, list) and "object" in schema_type):
        if schema.get("additionalProperties") is not False:
            return False
        properties = schema.get("properties", {})
        if properties:
            required = schema.get("required")
            if not isinstance(required, list) or set(required) != set(properties.keys()):
                return False
            for subschema in properties.values():
                if isinstance(subschema, dict) and not schema_supports_strict(subschema):
                    return False
    if schema_type == "array" or (isinstance(schema_type, list) and "array" in schema_type):
        items = schema.get("items")
        if isinstance(items, dict) and not schema_supports_strict(items):
            return False
    variants = schema.get("anyOf")
    if isinstance(variants, list):
        for variant in variants:
            if isinstance(variant, dict) and not schema_supports_strict(variant):
                return False
    return True


def build_payload(
    model: str,
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    max_output_tokens: int,
    thinking_effort: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": [message_to_input(message) for message in messages],
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": thinking_effort},
    }
    if schema and schema_supports_strict(schema):
        payload["text"] = {
            "format": {
                "type": "json_schema",
                "name": "normalized_output",
                "schema": schema,
                "strict": True,
            }
        }
    else:
        payload["text"] = {"format": {"type": "json_object"}}
    return payload


def payload_bytes(payload: dict[str, Any]) -> int | None:
    try:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return None
    return len(body.encode("utf-8"))
