from __future__ import annotations

from unittest.mock import MagicMock

import requests

from normalizer_vision.providers import OpenAIProvider, ProviderError, RateLimitError


def test_openai_provider_surface_exports_stable_symbols():
    assert ProviderError.__name__ == "ProviderError"
    assert RateLimitError.__name__ == "RateLimitError"


def test_openai_provider_parses_retry_after_numeric_and_http_date():
    assert OpenAIProvider._parse_retry_after("4") == 4.0
    assert OpenAIProvider._parse_retry_after("Wed, 01 Jan 2099 00:00:00 GMT") is not None


def test_openai_provider_rejects_past_retry_after_dates():
    assert OpenAIProvider._parse_retry_after("Wed, 01 Jan 2015 00:00:00 GMT") is None


def test_openai_provider_is_available_returns_false_for_invalid_key():
    provider = OpenAIProvider(api_key="invalid", model="gpt-5.4-mini")
    assert provider.is_available() is False


def test_openai_provider_is_available_returns_false_when_transport_fails():
    transport = MagicMock()
    transport.get.side_effect = requests.RequestException("offline")
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini", transport=transport)
    assert provider.is_available() is False
