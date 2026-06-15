"""Provider factory for orchestrator-owned runtime auth modes."""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from ..models.config import NormalizerExecutionConfig
from .anthropic_surface import AnthropicProvider
from .base import ProviderError
from .chat_surface import OpenAIChatProvider
from .google_surface import GoogleProvider
from .oauth_surface import OAuthProvider
from .surface import OpenAIProvider

_RUNTIME_PROVIDER_ID_ENV = "VISION_PROVIDER_ID"
_RUNTIME_PROVIDER_FAMILY_ENV = "VISION_PROVIDER_FAMILY"
_RUNTIME_PROVIDER_BASE_URL_ENV = "VISION_PROVIDER_BASE_URL"
_RUNTIME_AUTH_MODE_ENV = "VISION_PROVIDER_AUTH_MODE"
_RUNTIME_API_KEY_ENV = "VISION_PROVIDER_API_KEY"
_OAUTH_ACCESS_TOKEN_ENV = "VISION_PROVIDER_OAUTH_ACCESS_TOKEN"
_OAUTH_ACCOUNT_ID_ENV = "VISION_PROVIDER_OAUTH_ACCOUNT_ID"
_LEGACY_RUNTIME_AUTH_MODE_ENV = "VISION_OPENAI_AUTH_MODE"
_LEGACY_SHARED_API_KEY_ENV = "VISION_OPENAI_API_KEY"
_LEGACY_OAUTH_ACCESS_TOKEN_ENV = "VISION_OPENAI_OAUTH_ACCESS_TOKEN"
_LEGACY_OAUTH_ACCOUNT_ID_ENV = "VISION_OPENAI_OAUTH_ACCOUNT_ID"
_ALLOWED_AUTH_MODES = frozenset({"api_keys", "oauth"})
_DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def _normalized_base_url(value: str | None) -> str:
    return str(value or "").strip().rstrip("/") or _DEFAULT_OPENAI_BASE_URL


def _provider_name_for(base_url: str, provider_name: str | None) -> str:
    candidate = str(provider_name or "").strip().lower()
    if candidate:
        return candidate
    return "openai" if base_url == _DEFAULT_OPENAI_BASE_URL else "openai_compat"


def _provider_family_for(provider_name: str, base_url: str, provider_family: str | None) -> str:
    candidate = str(provider_family or "").strip().lower()
    if candidate:
        return candidate
    if provider_name == "anthropic":
        return "anthropic_messages"
    if provider_name == "google":
        return "google_gemini"
    if provider_name in {"openai", "xai", "openrouter", "groq"}:
        return "openai_responses"
    if provider_name == "openai_compat" and base_url == _DEFAULT_OPENAI_BASE_URL:
        return "openai_responses"
    return "openai_chat"


def _provider_requires_api_key(provider_name: str) -> bool:
    return provider_name not in {"openai_compat", "lmstudio", "ollama"}


def create_provider(
    config: NormalizerExecutionConfig,
    *,
    environ: Mapping[str, str] | None = None,
    transport: Any | None = None,
):
    env = os.environ if environ is None else environ
    auth_mode = str(env.get(_RUNTIME_AUTH_MODE_ENV) or env.get(_LEGACY_RUNTIME_AUTH_MODE_ENV, "")).strip().lower()
    if auth_mode not in _ALLOWED_AUTH_MODES:
        raise ProviderError(
            "Normalizer-LLM-Laeufe erfordern orchestrator-injizierte Runtime-Credentials "
            f"ueber {_RUNTIME_AUTH_MODE_ENV}=api_keys|oauth."
        )
    base_url = _normalized_base_url(env.get(_RUNTIME_PROVIDER_BASE_URL_ENV) or env.get("OPENAI_API_BASE_URL"))
    provider_name = _provider_name_for(base_url, env.get(_RUNTIME_PROVIDER_ID_ENV, ""))
    provider_family = _provider_family_for(provider_name, base_url, env.get(_RUNTIME_PROVIDER_FAMILY_ENV, ""))
    if auth_mode == "api_keys":
        api_key = str(env.get(_RUNTIME_API_KEY_ENV) or env.get(_LEGACY_SHARED_API_KEY_ENV, "")).strip()
        if not api_key and _provider_requires_api_key(provider_name):
            raise ProviderError(f"Orchestrator-API-Key fehlt: {_RUNTIME_API_KEY_ENV} nicht gesetzt.")
        if provider_family == "openai_responses":
            return OpenAIProvider(api_key=api_key, model=config.model, base_url=base_url, timeout=config.timeout_seconds, transport=transport, provider_name=provider_name)
        if provider_family == "openai_chat":
            return OpenAIChatProvider(api_key=api_key, model=config.model, base_url=base_url, timeout=config.timeout_seconds, transport=transport, provider_name=provider_name)
        if provider_family == "anthropic_messages":
            return AnthropicProvider(api_key=api_key, model=config.model, base_url=base_url, timeout=config.timeout_seconds, transport=transport, provider_name=provider_name)
        if provider_family == "google_gemini":
            return GoogleProvider(api_key=api_key, model=config.model, base_url=base_url, timeout=config.timeout_seconds, transport=transport, provider_name=provider_name)
        raise ProviderError(f"Nicht unterstuetzte Provider-Familie: {provider_family}")
    access_token = str(env.get(_OAUTH_ACCESS_TOKEN_ENV) or env.get(_LEGACY_OAUTH_ACCESS_TOKEN_ENV, "")).strip()
    if not access_token:
        raise ProviderError(f"Orchestrator-OAuth fehlt: {_OAUTH_ACCESS_TOKEN_ENV} nicht gesetzt.")
    return OAuthProvider(
        access_token=access_token,
        account_id=str(env.get(_OAUTH_ACCOUNT_ID_ENV) or env.get(_LEGACY_OAUTH_ACCOUNT_ID_ENV, "")).strip(),
        model=config.model,
        timeout=config.timeout_seconds,
    )
