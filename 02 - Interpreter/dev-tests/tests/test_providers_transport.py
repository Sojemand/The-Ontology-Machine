"""Tests for OpenAI provider transport helpers."""
from __future__ import annotations

import socket
import urllib.error
from unittest.mock import patch

import pytest

from llm_interpreter.providers import OpenAIProvider, ProviderError


def test_parse_retry_after_accepts_http_date():
    retry_after = OpenAIProvider._parse_retry_after("Wed, 21 Oct 2099 07:28:00 GMT")
    assert retry_after is not None
    assert retry_after > 0


def test_parse_retry_after_rejects_past_dates():
    assert OpenAIProvider._parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") is None


def test_request_wraps_socket_timeout_as_provider_error():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4", timeout=12)
    with patch("llm_interpreter.providers.openai_transport.urllib.request.urlopen", side_effect=socket.timeout()):
        with pytest.raises(ProviderError, match="Timeout"):
            provider._request("GET", "/models")


def test_request_wraps_urlerror_as_provider_error():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4")
    with patch(
        "llm_interpreter.providers.openai_transport.urllib.request.urlopen",
        side_effect=urllib.error.URLError("down"),
    ):
        with pytest.raises(ProviderError, match="nicht erreichbar"):
            provider._request("GET", "/models")
