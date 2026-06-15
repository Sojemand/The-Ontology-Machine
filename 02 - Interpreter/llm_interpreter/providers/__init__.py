"""Provider factory for orchestrator-owned runtime auth and provider families."""
from __future__ import annotations

import os

from .anthropic_surface import AnthropicProvider
from .base import LLMProvider, ProviderError, RateLimitError
from .google_surface import GoogleProvider
from .oauth_surface import OAuthProvider
from .openai_chat_surface import OpenAIChatProvider
from .openai_surface import OpenAIProvider

_PROVIDER_ID_ENV = "VISION_PROVIDER_ID"
_PROVIDER_FAMILY_ENV = "VISION_PROVIDER_FAMILY"
_PROVIDER_BASE_URL_ENV = "VISION_PROVIDER_BASE_URL"
_AUTH_MODE_ENV = "VISION_PROVIDER_AUTH_MODE"
_API_KEY_ENV = "VISION_PROVIDER_API_KEY"
_OAUTH_ACCESS_TOKEN_ENV = "VISION_PROVIDER_OAUTH_ACCESS_TOKEN"
_OAUTH_ACCOUNT_ID_ENV = "VISION_PROVIDER_OAUTH_ACCOUNT_ID"
_DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def _normalized_base_url(value: str | None) -> str:
    return str(value or "").strip().rstrip("/") or _DEFAULT_OPENAI_BASE_URL


def _provider_name_for(base_url: str, explicit_provider_name: str | None) -> str:
    candidate = str(explicit_provider_name or "").strip().lower()
    if candidate:
        return candidate
    if base_url == _DEFAULT_OPENAI_BASE_URL:
        return "openai"
    return "openai_compat"


def _provider_family_for(provider_name: str, base_url: str, explicit_family: str | None) -> str:
    family = str(explicit_family or "").strip().lower()
    if family:
        return family
    if provider_name == "anthropic":
        return "anthropic_messages"
    if provider_name == "google":
        return "google_gemini"
    if provider_name in {"openai", "xai", "groq"}:
        return "openai_responses"
    if provider_name == "openai_compat" and base_url == _DEFAULT_OPENAI_BASE_URL:
        return "openai_responses"
    return "openai_chat"


def _provider_requires_api_key(provider_name: str) -> bool:
    return provider_name not in {"openai_compat", "lmstudio", "ollama"}


def create_provider(model: str | None = None, **kwargs) -> LLMProvider:
    runtime_mode = str(
        kwargs.get("auth_mode")
        or os.getenv(_AUTH_MODE_ENV, "")
    ).strip().lower()
    timeout = kwargs.get("timeout", 300)
    resolved_model = str(model or "gpt-5.4").strip() or "gpt-5.4"
    if not runtime_mode:
        raise ProviderError(f"{_AUTH_MODE_ENV} nicht gesetzt")
    if runtime_mode not in {"api_keys", "oauth"}:
        raise ProviderError(f"{_AUTH_MODE_ENV} ungueltig: {runtime_mode}")
    base_url = _normalized_base_url(
        kwargs.get("base_url")
        or os.getenv(_PROVIDER_BASE_URL_ENV, "")
        or os.getenv("OPENAI_API_BASE_URL", _DEFAULT_OPENAI_BASE_URL)
    )
    provider_name = _provider_name_for(
        base_url,
        kwargs.get("provider_name") or os.getenv(_PROVIDER_ID_ENV, ""),
    )
    provider_family = _provider_family_for(
        provider_name,
        base_url,
        kwargs.get("provider_family") or os.getenv(_PROVIDER_FAMILY_ENV, ""),
    )
    if runtime_mode == "oauth":
        if provider_family not in {"openai_responses", "openai_oauth"}:
            raise ProviderError("OAuth-Laufzeit ist aktuell nur fuer OpenAI-Providerfamilien verfuegbar")
        access_token = str(
            kwargs.get("access_token")
            or os.getenv(_OAUTH_ACCESS_TOKEN_ENV, "")
        ).strip()
        if not access_token:
            raise ProviderError(f"{_OAUTH_ACCESS_TOKEN_ENV} nicht gesetzt")
        return OAuthProvider(
            access_token=access_token,
            account_id=str(
                kwargs.get("account_id")
                or os.getenv(_OAUTH_ACCOUNT_ID_ENV, "")
            ).strip(),
            model=resolved_model,
            timeout=timeout,
        )
    api_key = str(
        kwargs.get("api_key")
        if kwargs.get("api_key") is not None
        else os.getenv(_API_KEY_ENV, "")
    ).strip()
    if not api_key and _provider_requires_api_key(provider_name):
        raise ProviderError(f"{_API_KEY_ENV} nicht gesetzt")
    if provider_family == "openai_responses":
        return OpenAIProvider(api_key=api_key, model=resolved_model, base_url=base_url, timeout=timeout, provider_name=provider_name)
    if provider_family == "openai_chat":
        return OpenAIChatProvider(api_key=api_key, model=resolved_model, base_url=base_url, timeout=timeout, provider_name=provider_name)
    if provider_family == "anthropic_messages":
        return AnthropicProvider(api_key=api_key, model=resolved_model, base_url=base_url, timeout=timeout, provider_name=provider_name)
    if provider_family == "google_gemini":
        return GoogleProvider(api_key=api_key, model=resolved_model, base_url=base_url, timeout=timeout, provider_name=provider_name)
    raise ProviderError(f"Nicht unterstuetzte Provider-Familie: {provider_family}")


__all__ = [
    "AnthropicProvider",
    "GoogleProvider",
    "LLMProvider",
    "OAuthProvider",
    "OpenAIChatProvider",
    "OpenAIProvider",
    "ProviderError",
    "RateLimitError",
    "create_provider",
]
