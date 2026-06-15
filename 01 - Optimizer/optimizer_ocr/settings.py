"""Environment-backed settings for the Optimizer OCR port."""

from __future__ import annotations

from dataclasses import dataclass
import os

from .errors import LlmOcrConfigurationError


@dataclass(frozen=True)
class LlmOcrSettings:
    provider_id: str
    provider_family: str
    base_url: str
    auth_mode: str
    api_key: str
    oauth_access_token: str
    oauth_account_id: str
    model: str
    max_output_tokens: int
    timeout_seconds: int

    @property
    def bearer_token(self) -> str:
        if self.auth_mode == "oauth":
            return self.oauth_access_token
        return self.api_key


_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_PROVIDER_ID = "openai"
_DEFAULT_PROVIDER_FAMILY = "openai_responses"
_DEFAULT_MAX_OUTPUT_TOKENS = 4096
_DEFAULT_TIMEOUT_SECONDS = 120
_API_KEY_OPTIONAL_PROVIDERS = {"lmstudio", "ollama", "openai_compat"}
RESPONSES_FAMILIES = {"openai_responses", "openai", "responses"}
CHAT_FAMILIES = {"openai_chat", "chat", "openai_compat"}


def settings_from_env(*, timeout_seconds: int | None = None) -> LlmOcrSettings:
    env = os.environ
    provider_id = _env_text("OPTIMIZER_OCR_PROVIDER_ID", default=_DEFAULT_PROVIDER_ID)
    provider_family = _env_text("OPTIMIZER_OCR_PROVIDER_FAMILY", default=_DEFAULT_PROVIDER_FAMILY).lower()
    if provider_family not in RESPONSES_FAMILIES and provider_family not in CHAT_FAMILIES:
        raise LlmOcrConfigurationError(f"optimizer_ocr Provider-Family wird nicht unterstuetzt: {provider_family}")
    base_url = _env_text("OPTIMIZER_OCR_BASE_URL", default=_DEFAULT_BASE_URL).rstrip("/")
    auth_mode = _env_text("OPTIMIZER_OCR_AUTH_MODE", default="api_keys").lower()
    if auth_mode == "api_key":
        auth_mode = "api_keys"
    model = _env_text("OPTIMIZER_OCR_MODEL")
    if not model:
        raise LlmOcrConfigurationError("optimizer_ocr Modell fehlt.")
    if not base_url:
        raise LlmOcrConfigurationError("optimizer_ocr Base-URL fehlt.")
    api_key = str(env.get("OPTIMIZER_OCR_API_KEY") or "").strip()
    oauth_access_token = str(env.get("OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN") or "").strip()
    oauth_account_id = str(env.get("OPTIMIZER_OCR_OAUTH_ACCOUNT_ID") or "").strip()
    if auth_mode == "oauth":
        if not oauth_access_token:
            raise LlmOcrConfigurationError("optimizer_ocr OAuth-Token fehlt.")
    elif auth_mode not in {"none", "local"}:
        if not api_key and provider_id not in _API_KEY_OPTIONAL_PROVIDERS:
            raise LlmOcrConfigurationError("optimizer_ocr API-Key fehlt.")
        auth_mode = "api_keys"
    return LlmOcrSettings(
        provider_id=provider_id,
        provider_family=provider_family,
        base_url=base_url,
        auth_mode=auth_mode,
        api_key=api_key,
        oauth_access_token=oauth_access_token,
        oauth_account_id=oauth_account_id,
        model=model,
        max_output_tokens=_env_int("OPTIMIZER_OCR_MAX_OUTPUT_TOKENS", _DEFAULT_MAX_OUTPUT_TOKENS),
        timeout_seconds=timeout_seconds or _env_int("OPTIMIZER_OCR_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS),
    )


def _env_text(name: str, *, default: str = "") -> str:
    return str(os.environ.get(name) or default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        value = int(str(os.environ.get(name) or default).strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default
