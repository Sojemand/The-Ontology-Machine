from __future__ import annotations

import pytest

from normalizer_vision.models import NormalizerProjectConfig, NormalizerRuntimeSettings
from normalizer_vision.providers import (
    AnthropicProvider,
    GoogleProvider,
    OAuthProvider,
    OpenAIChatProvider,
    OpenAIProvider,
    ProviderError,
    create_provider,
)


def _execution_config(
    *,
    model: str = "gpt-5.4-mini",
    max_output_tokens: int = 15_000,
    structured_outputs: bool = True,
):
    project_config = NormalizerProjectConfig(structured_outputs=structured_outputs)
    runtime_settings = NormalizerRuntimeSettings(model=model, max_output_tokens=max_output_tokens)
    return project_config.build_execution_config(runtime_settings)


def test_create_provider_requires_explicit_runtime_auth_mode():
    with pytest.raises(ProviderError, match="VISION_PROVIDER_AUTH_MODE=api_keys\\|oauth"):
        create_provider(_execution_config(), environ={})


def test_create_provider_uses_shared_api_key_runtime_only():
    provider = create_provider(
        _execution_config(),
        environ={
            "VISION_PROVIDER_AUTH_MODE": "api_keys",
            "VISION_PROVIDER_API_KEY": "sk-orchestrator",
            "OPENAI_API_KEY": "sk-global",
            "NORMALIZER_OPENAI_API_KEY": "sk-local",
        },
    )

    assert isinstance(provider, OpenAIProvider)
    assert provider.api_key == "sk-orchestrator"


def test_create_provider_api_keys_does_not_fallback_to_legacy_env():
    with pytest.raises(ProviderError, match="VISION_PROVIDER_API_KEY"):
        create_provider(
            _execution_config(),
            environ={
                "VISION_PROVIDER_AUTH_MODE": "api_keys",
                "OPENAI_API_KEY": "sk-global",
                "NORMALIZER_OPENAI_API_KEY": "sk-local",
            },
        )


def test_create_provider_allows_openai_compatible_runtime_without_api_key():
    provider = create_provider(
        _execution_config(model="qwen/qwen3-4b", structured_outputs=False),
        environ={
            "VISION_PROVIDER_ID": "openai_compat",
            "VISION_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "VISION_PROVIDER_AUTH_MODE": "api_keys",
        },
    )

    assert isinstance(provider, OpenAIChatProvider)
    assert provider.provider_name == "openai_compat"
    assert provider.api_key == ""
    assert provider.base_url == "http://127.0.0.1:1234/v1"


def test_create_provider_uses_anthropic_family():
    provider = create_provider(
        _execution_config(model="claude-sonnet-4-20250514"),
        environ={
            "VISION_PROVIDER_ID": "anthropic",
            "VISION_PROVIDER_BASE_URL": "https://api.anthropic.com/v1",
            "VISION_PROVIDER_AUTH_MODE": "api_keys",
            "VISION_PROVIDER_API_KEY": "anthropic-test",
        },
    )

    assert isinstance(provider, AnthropicProvider)
    assert provider.provider_name == "anthropic"


def test_create_provider_uses_google_family():
    provider = create_provider(
        _execution_config(model="gemini-2.5-flash"),
        environ={
            "VISION_PROVIDER_ID": "google",
            "VISION_PROVIDER_BASE_URL": "https://generativelanguage.googleapis.com/v1beta",
            "VISION_PROVIDER_AUTH_MODE": "api_keys",
            "VISION_PROVIDER_API_KEY": "google-test",
        },
    )

    assert isinstance(provider, GoogleProvider)
    assert provider.provider_name == "google"


def test_create_provider_uses_oauth_runtime():
    provider = create_provider(
        _execution_config(model="gpt-5.4"),
        environ={
            "VISION_PROVIDER_AUTH_MODE": "oauth",
            "VISION_PROVIDER_OAUTH_ACCESS_TOKEN": "oauth-token-123",
            "VISION_PROVIDER_OAUTH_ACCOUNT_ID": "account-1",
            "VISION_PROVIDER_API_KEY": "sk-orchestrator",
        },
    )

    assert isinstance(provider, OAuthProvider)
    assert provider.access_token == "oauth-token-123"
    assert provider.account_id == "account-1"


def test_create_provider_oauth_does_not_fallback_to_api_key():
    with pytest.raises(ProviderError, match="VISION_PROVIDER_OAUTH_ACCESS_TOKEN"):
        create_provider(
            _execution_config(),
            environ={
                "VISION_PROVIDER_AUTH_MODE": "oauth",
                "VISION_PROVIDER_API_KEY": "sk-orchestrator",
            },
        )


def test_create_provider_oauth_accepts_orchestrator_runtime_settings():
    provider = create_provider(
        _execution_config(model="gpt-5.4-mini", max_output_tokens=12_345, structured_outputs=False),
        environ={
            "VISION_PROVIDER_AUTH_MODE": "oauth",
            "VISION_PROVIDER_OAUTH_ACCESS_TOKEN": "oauth-token-123",
            "VISION_PROVIDER_OAUTH_ACCOUNT_ID": "account-1",
        },
    )

    assert isinstance(provider, OAuthProvider)
