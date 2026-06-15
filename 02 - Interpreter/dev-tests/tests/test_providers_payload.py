"""Tests for OpenAI provider payload construction."""
from __future__ import annotations

import pytest

from llm_interpreter.models import InterpreterConfig, VISION_IMAGE_DETAIL
from llm_interpreter.prompts import build_vision_messages
from llm_interpreter.providers import OAuthProvider, OpenAIChatProvider, OpenAIProvider, ProviderError, oauth_transport


def _strict_schema() -> dict:
    return {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }


def test_build_payload_uses_json_object(sample_request):
    messages = build_vision_messages(sample_request, InterpreterConfig())
    payload = OpenAIProvider.build_payload(
        model="gpt-5.4",
        messages=messages,
        schema=None,
        max_output_tokens=8000,
        thinking_effort="medium",
    )
    assert payload["model"] == "gpt-5.4"
    assert payload["reasoning"] == {"effort": "medium"}
    assert payload["text"]["format"]["type"] == "json_object"
    assert payload["input"][1]["content"][1]["detail"] == VISION_IMAGE_DETAIL


def test_build_payload_uses_strict_json_schema_when_schema_is_supplied(sample_request):
    messages = build_vision_messages(sample_request, InterpreterConfig())
    schema = _strict_schema()

    payload = OpenAIProvider.build_payload(
        model="gpt-5.4",
        messages=messages,
        schema=schema,
        max_output_tokens=8000,
        thinking_effort="medium",
    )

    text_format = payload["text"]["format"]
    assert text_format["type"] == "json_schema"
    assert text_format["name"] == "kernel_llm_output"
    assert text_format["strict"] is True
    assert text_format["schema"] == schema
    assert text_format["schema"] is not schema


def test_oauth_provider_forwards_strict_json_schema(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_backend_content_response(**kwargs):
        captured.update(kwargs)
        return oauth_transport.TransportResult(
            success=True,
            status_code=200,
            output_text='{"ok":true}',
            response_id="resp_123",
            usage={"input_tokens": 1, "output_tokens": 1},
        )

    monkeypatch.setattr(
        "llm_interpreter.providers.oauth_surface.oauth_transport.run_backend_content_response",
        _fake_run_backend_content_response,
    )
    schema = _strict_schema()
    provider = OAuthProvider(access_token="token-secret", account_id="account-1", model="gpt-5.4")

    output_text = provider.generate(
        messages=[{"role": "user", "content": "Return JSON"}],
        schema=schema,
        max_output_tokens=512,
        thinking_effort="none",
    )

    assert output_text == '{"ok":true}'
    text_format = captured["text_format"]
    assert text_format["type"] == "json_schema"
    assert text_format["name"] == "kernel_llm_output"
    assert text_format["strict"] is True
    assert text_format["schema"] == schema


def test_chat_payload_uses_strict_json_schema_when_schema_is_supplied():
    schema = _strict_schema()

    payload = OpenAIChatProvider.build_payload(
        model="gpt-5.4",
        messages=[{"role": "user", "content": "Return JSON"}],
        schema=schema,
        max_output_tokens=512,
        thinking_effort="none",
    )

    response_format = payload["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"] == {
        "name": "kernel_llm_output",
        "strict": True,
        "schema": schema,
    }
    assert response_format["json_schema"]["schema"] is not schema


def test_message_to_input_rejects_non_list_content():
    with pytest.raises(ProviderError, match="Nachrichtenformat"):
        OpenAIProvider._message_to_input({"role": "user", "content": {"bad": "shape"}})


def test_message_to_input_rejects_invalid_blocks():
    with pytest.raises(ProviderError, match="Inhaltsblock"):
        OpenAIProvider._message_to_input({"role": "user", "content": ["bad-block"]})


def test_message_to_input_rejects_unsupported_block_types():
    with pytest.raises(ProviderError, match="Nicht unterstuetzter Inhaltsblock"):
        OpenAIProvider._message_to_input({"role": "user", "content": [{"type": "audio"}]})
