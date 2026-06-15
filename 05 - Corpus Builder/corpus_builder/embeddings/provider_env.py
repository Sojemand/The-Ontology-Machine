"""Embedding provider environment resolution."""

from __future__ import annotations

import os
import re

from .types import RuntimeEmbeddingsCapability

RUNTIME_PROVIDER_ID_ENV = "VISION_PROVIDER_ID"
RUNTIME_PROVIDER_FAMILY_ENV = "VISION_PROVIDER_FAMILY"
RUNTIME_BASE_URL_ENV = "VISION_PROVIDER_BASE_URL"
RUNTIME_API_KEY_ENV = "VISION_PROVIDER_API_KEY"
LEGACY_RUNTIME_BASE_URL_ENV = "OPENAI_API_BASE_URL"
LEGACY_RUNTIME_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

_SECRET_PATTERN = re.compile(r"(?:sk-[A-Za-z0-9_-]+|Bearer\s+[A-Za-z0-9._-]+)", re.IGNORECASE)


def normalized_value(value: str | None) -> str:
    return str(value or "").strip()


def normalized_base_url(value: str | None) -> str:
    return normalized_value(value).rstrip("/")


def resolved_api_key(value: str | None = None) -> str | None:
    explicit = normalized_value(value)
    if explicit:
        return explicit
    injected = normalized_value(os.getenv(RUNTIME_API_KEY_ENV) or os.getenv(LEGACY_RUNTIME_API_KEY_ENV))
    return injected or None


def resolved_base_url(value: str | None = None, *, default_if_missing: bool = True) -> str:
    explicit = normalized_base_url(value)
    if explicit:
        return explicit
    injected = normalized_base_url(os.getenv(RUNTIME_BASE_URL_ENV) or os.getenv(LEGACY_RUNTIME_BASE_URL_ENV))
    if injected:
        return injected
    return DEFAULT_OPENAI_BASE_URL if default_if_missing else ""


def resolved_provider_id(base_url: str | None = None) -> str:
    injected = normalized_value(os.getenv(RUNTIME_PROVIDER_ID_ENV)).lower()
    if injected:
        return injected
    base_url = resolved_base_url(base_url)
    if base_url.startswith(DEFAULT_OPENAI_BASE_URL):
        return "openai"
    if base_url:
        return "openai_compat"
    return ""


def resolved_provider_family(*, provider_id: str | None = None, base_url: str | None = None) -> str:
    injected = normalized_value(os.getenv(RUNTIME_PROVIDER_FAMILY_ENV)).lower()
    if injected:
        return injected
    resolved_id = str(provider_id or resolved_provider_id(base_url)).strip().lower()
    if resolved_id == "google":
        return "google_gemini"
    if resolved_id in {"openai", "xai", "openrouter", "groq"}:
        return "openai_responses"
    return "openai_chat"


def request_headers(api_key: str | None = None, *, provider_family: str = "openai_chat") -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    resolved_key = resolved_api_key(api_key)
    if resolved_key:
        if provider_family == "google_gemini":
            headers["x-goog-api-key"] = resolved_key
        else:
            headers["Authorization"] = f"Bearer {resolved_key}"
    return headers


def resolve_runtime_capability(*, env_name: str = RUNTIME_API_KEY_ENV) -> RuntimeEmbeddingsCapability:
    api_key = resolved_api_key(os.getenv(env_name))
    base_url = resolved_base_url(default_if_missing=False)
    if not base_url and api_key:
        base_url = DEFAULT_OPENAI_BASE_URL
    if not base_url:
        return RuntimeEmbeddingsCapability(
            status="unavailable",
            reason="Keine Embeddings-API vom Orchestrator bereitgestellt.",
        )
    return RuntimeEmbeddingsCapability(
        status="available",
        api_key=api_key,
        provider_id=resolved_provider_id(base_url),
        provider_family=resolved_provider_family(base_url=base_url),
        base_url=base_url,
    )


def sanitize_reason(text: str) -> str:
    cleaned = _SECRET_PATTERN.sub("[redacted]", str(text or ""))
    return cleaned.strip()
