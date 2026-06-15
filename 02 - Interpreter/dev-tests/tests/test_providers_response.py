"""Tests for OpenAI provider response handling."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from llm_interpreter.providers import OpenAIProvider, ProviderError, RateLimitError


def test_generate_returns_output_text():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch.object(
        provider,
        "_request",
        return_value=(200, {}, json.dumps({"id": "resp_123", "model": "gpt-5.4", "usage": {"input_tokens": 123, "output_tokens": 45}, "output_text": '{"ok":true}'})),
    ) as mock_request:
        result = provider.generate(
            messages=[{"role": "user", "content": [{"type": "text", "text": "test"}]}],
            schema=None,
            max_output_tokens=200,
            thinking_effort="none",
        )
    assert result == '{"ok":true}'
    payload = mock_request.call_args.kwargs["payload"]
    assert payload["reasoning"] == {"effort": "none"}
    assert payload["max_output_tokens"] == 200


def test_generate_falls_back_to_output_content():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch.object(
        provider,
        "_request",
        return_value=(200, {}, json.dumps({"model": "gpt-5.4", "usage": {}, "output": [{"content": [{"type": "output_text", "text": '{"fallback":true}'}]}]})),
    ):
        result = provider.generate(messages=[{"role": "user", "content": "test"}], schema=None, max_output_tokens=100, thinking_effort="high")
    assert result == '{"fallback":true}'


def test_rate_limit_raises():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch.object(provider, "_request", return_value=(429, {"retry-after": "7"}, "")):
        with pytest.raises(RateLimitError) as exc_info:
            provider.generate([{"role": "user", "content": "x"}], None, 100, "low")
    assert exc_info.value.retry_after == 7.0


def test_invalid_retry_after_header_falls_back_to_none():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch.object(provider, "_request", return_value=(429, {"retry-after": "not-a-number"}, "")):
        with pytest.raises(RateLimitError) as exc_info:
            provider.generate([{"role": "user", "content": "x"}], None, 100, "low")
    assert exc_info.value.retry_after is None


def test_error_includes_status_code():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch.object(provider, "_request", return_value=(500, {}, "boom")):
        with pytest.raises(ProviderError, match="500"):
            provider.generate([{"role": "user", "content": "x"}], None, 100, "low")


def test_invalid_json_is_wrapped_as_provider_error():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch.object(provider, "_request", return_value=(200, {}, "{broken-json")):
        with pytest.raises(ProviderError, match="ungueltiges JSON"):
            provider.generate([{"role": "user", "content": "x"}], None, 100, "low")


def test_non_dict_json_payload_is_rejected():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch.object(provider, "_request", return_value=(200, {}, json.dumps(["bad"]))):
        with pytest.raises(ProviderError, match="ungueltiges Antwortobjekt"):
            provider.generate([{"role": "user", "content": "x"}], None, 100, "low")


def test_missing_text_output_raises_provider_error():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch.object(provider, "_request", return_value=(200, {}, json.dumps({"model": "gpt-5.4", "usage": {}, "output": ["bad"]}))):
        with pytest.raises(ProviderError, match="keinen Text-Output"):
            provider.generate([{"role": "user", "content": "x"}], None, 100, "low")
