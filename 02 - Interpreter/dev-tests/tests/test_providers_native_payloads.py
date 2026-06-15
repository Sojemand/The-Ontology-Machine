from __future__ import annotations

import json

from llm_interpreter.models import InterpreterConfig
from llm_interpreter.prompts import build_vision_messages
from llm_interpreter.providers import AnthropicProvider, GoogleProvider
from llm_interpreter.providers.anthropic_response import parse_response


def _strict_schema() -> dict:
    return {
        "type": "object",
        "properties": {"ok": {"type": "string"}},
        "required": ["ok"],
        "additionalProperties": False,
    }


def test_anthropic_provider_builds_payload_without_target_schema(sample_request):
    messages = build_vision_messages(sample_request, InterpreterConfig())

    payload = AnthropicProvider.build_payload(
        model="claude-sonnet-4-20250514",
        messages=messages,
        schema=None,
        max_output_tokens=4000,
        thinking_effort="none",
    )

    assert "tools" not in payload
    assert "tool_choice" not in payload
    assert "output_config" not in payload
    assert payload["messages"][0]["content"][0]["type"] == "text"
    assert payload["messages"][0]["content"][1]["type"] == "image"


def test_anthropic_provider_uses_native_json_schema_output_config(sample_request):
    messages = build_vision_messages(sample_request, InterpreterConfig())
    schema = _strict_schema()

    payload = AnthropicProvider.build_payload(
        model="claude-sonnet-4-20250514",
        messages=messages,
        schema=schema,
        max_output_tokens=4000,
        thinking_effort="none",
    )

    output_format = payload["output_config"]["format"]
    assert output_format["type"] == "json_schema"
    assert output_format["schema"] == schema
    assert output_format["schema"] is not schema


def test_anthropic_provider_reads_json_from_text_response():
    response = {
        "id": "msg_1",
        "model": "claude-sonnet-4-20250514",
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "content": [{"type": "text", "text": "{\"ok\":true}"}],
    }

    parsed = parse_response(json.dumps(response), fallback_model="fallback")

    assert parsed.output_text == "{\"ok\":true}"
    assert parsed.model == "claude-sonnet-4-20250514"
    assert parsed.response_id == "msg_1"


def test_google_provider_builds_json_mode_without_target_schema(sample_request):
    messages = build_vision_messages(sample_request, InterpreterConfig())

    payload = GoogleProvider.build_payload(
        model="gemini-2.5-flash",
        messages=messages,
        schema=None,
        max_output_tokens=4000,
        thinking_effort="none",
    )

    assert "responseJsonSchema" not in payload["generationConfig"]
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert payload["contents"][0]["parts"][0]["text"]
    assert payload["contents"][0]["parts"][1]["inlineData"]["data"]


def test_google_provider_uses_native_response_json_schema(sample_request):
    messages = build_vision_messages(sample_request, InterpreterConfig())
    schema = _strict_schema()

    payload = GoogleProvider.build_payload(
        model="gemini-2.5-flash",
        messages=messages,
        schema=schema,
        max_output_tokens=4000,
        thinking_effort="none",
    )

    generation_config = payload["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert generation_config["responseJsonSchema"] == schema
    assert generation_config["responseJsonSchema"] is not schema
