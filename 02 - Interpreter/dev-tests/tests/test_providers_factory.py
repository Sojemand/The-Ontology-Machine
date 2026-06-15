"""Tests for provider factory and thinking-effort mapping."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from llm_interpreter.models import InterpreterConfig
from llm_interpreter.providers import AnthropicProvider, GoogleProvider, ProviderError, create_provider


def test_create_provider_is_openai_only():
    with patch.dict(
        "os.environ",
        {"VISION_PROVIDER_AUTH_MODE": "api_keys", "VISION_PROVIDER_API_KEY": "sk-test"},
        clear=True,
    ):
        provider = create_provider("gpt-5.4")
    assert provider.provider_name == "openai"
    assert provider.model == "gpt-5.4"


def test_create_provider_requires_auth_mode():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ProviderError, match="VISION_PROVIDER_AUTH_MODE"):
            create_provider("gpt-5.4")


def test_create_provider_requires_shared_runtime_api_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ProviderError, match="VISION_PROVIDER_API_KEY"):
            create_provider("gpt-5.4", auth_mode="api_keys")


def test_create_provider_rejects_legacy_openai_api_key_fallback():
    with patch.dict(
        "os.environ",
        {"VISION_PROVIDER_AUTH_MODE": "api_keys", "OPENAI_API_KEY": "sk-legacy"},
        clear=True,
    ):
        with pytest.raises(ProviderError, match="VISION_PROVIDER_API_KEY"):
            create_provider("gpt-5.4")


def test_create_provider_rejects_legacy_vision_openai_overlay():
    with patch.dict(
        "os.environ",
        {"VISION_OPENAI_AUTH_MODE": "api_keys", "VISION_OPENAI_API_KEY": "sk-legacy"},
        clear=True,
    ):
        with pytest.raises(ProviderError, match="VISION_PROVIDER_AUTH_MODE"):
            create_provider("gpt-5.4")


def test_create_provider_allows_openai_compatible_runtime_without_api_key():
    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_ID": "openai_compat",
            "VISION_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "VISION_PROVIDER_AUTH_MODE": "api_keys",
        },
        clear=True,
    ):
        provider = create_provider("qwen/qwen3-4b")

    assert provider.provider_name == "openai_compat"
    assert provider.api_key == ""
    assert provider.base_url == "http://127.0.0.1:1234/v1"


def test_create_provider_uses_anthropic_family():
    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_ID": "anthropic",
            "VISION_PROVIDER_BASE_URL": "https://api.anthropic.com/v1",
            "VISION_PROVIDER_AUTH_MODE": "api_keys",
            "VISION_PROVIDER_API_KEY": "anthropic-test",
        },
        clear=True,
    ):
        provider = create_provider("claude-sonnet-4-20250514")

    assert isinstance(provider, AnthropicProvider)
    assert provider.provider_name == "anthropic"


def test_create_provider_uses_google_family():
    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_ID": "google",
            "VISION_PROVIDER_BASE_URL": "https://generativelanguage.googleapis.com/v1beta",
            "VISION_PROVIDER_AUTH_MODE": "api_keys",
            "VISION_PROVIDER_API_KEY": "google-test",
        },
        clear=True,
    ):
        provider = create_provider("gemini-2.5-flash")

    assert isinstance(provider, GoogleProvider)
    assert provider.provider_name == "google"


def test_create_provider_uses_orchestrator_oauth_runtime():
    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_AUTH_MODE": "oauth",
            "VISION_PROVIDER_OAUTH_ACCESS_TOKEN": "access-token",
            "VISION_PROVIDER_OAUTH_ACCOUNT_ID": "account-1",
        },
        clear=True,
    ):
        provider = create_provider("gpt-5.4")

    assert provider.provider_name == "openai_oauth"
    assert provider.model == "gpt-5.4"


def test_create_provider_does_not_fallback_from_oauth_to_api_key():
    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_AUTH_MODE": "oauth",
            "VISION_PROVIDER_API_KEY": "sk-test",
        },
        clear=True,
    ):
        with pytest.raises(ProviderError, match="VISION_PROVIDER_OAUTH_ACCESS_TOKEN"):
            create_provider("gpt-5.4")


def test_create_provider_ignores_legacy_model_env_fallback():
    with patch.dict(
        "os.environ",
        {"VISION_PROVIDER_AUTH_MODE": "api_keys", "VISION_PROVIDER_API_KEY": "sk-test", "LLM_MODEL": "gpt-4o"},
        clear=True,
    ):
        provider = create_provider()

    assert provider.model == "gpt-5.4"


def test_no_thinking_maps_to_none():
    assert InterpreterConfig(thinking_effort="no thinking").api_thinking_effort == "none"
