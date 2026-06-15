"""Soft policy defaults and labels for the orchestrator credentials subsystem."""

from __future__ import annotations

from hashlib import sha256

from ..models import ProviderEndpointSettings
from .oauth_types import OAuthTokenBundle
from .types import CredentialTarget, OAuthSessionState

TARGET_ORDER: tuple[CredentialTarget, ...] = ("llm_shared", "optimizer_ocr", "embeddings")
TARGET_LABELS: dict[CredentialTarget, str] = {
    "llm_shared": "LLM Shared API",
    "optimizer_ocr": "Optimizer OCR API",
    "embeddings": "Embeddings API",
}
SECRET_NAMES: dict[CredentialTarget, str] = {
    "llm_shared": "openai.llm_shared.api_key",
    "optimizer_ocr": "openai.optimizer_ocr.api_key",
    "embeddings": "openai.embeddings.api_key",
}
CAPABILITY_SPECS = (
    ("interpreter", "Interpreter", "llm_shared", ""),
    ("normalizer", "Normalizer", "llm_shared", ""),
    ("optimizer", "Optimizer OCR", "optimizer_ocr", ""),
    ("corpus_builder", "Corpus Builder Embeddings", "embeddings", "generate_embeddings"),
)
OAUTH_SUPPORTED_MODULES = frozenset({"interpreter", "normalizer", "optimizer"})
OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OAUTH_SCOPE = "openid profile email offline_access"
OAUTH_CALLBACK_PORT = 1455
OAUTH_BACKEND_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
RUNTIME_PROVIDER_ID_ENV = "VISION_PROVIDER_ID"
RUNTIME_PROVIDER_FAMILY_ENV = "VISION_PROVIDER_FAMILY"
RUNTIME_PROVIDER_BASE_URL_ENV = "VISION_PROVIDER_BASE_URL"
RUNTIME_AUTH_MODE_ENV = "VISION_PROVIDER_AUTH_MODE"
RUNTIME_API_KEY_ENV = "VISION_PROVIDER_API_KEY"
RUNTIME_OAUTH_ACCESS_TOKEN_ENV = "VISION_PROVIDER_OAUTH_ACCESS_TOKEN"
RUNTIME_OAUTH_ACCOUNT_ID_ENV = "VISION_PROVIDER_OAUTH_ACCOUNT_ID"
RUNTIME_OAUTH_CLIENT_ID_ENV = "VISION_PROVIDER_OAUTH_CLIENT_ID"
RUNTIME_OAUTH_SESSION_ID_ENV = "VISION_PROVIDER_OAUTH_SESSION_ID"
RUNTIME_OAUTH_SCOPE_ENV = "VISION_PROVIDER_OAUTH_SCOPE"
RUNTIME_OAUTH_EXPIRES_AT_ENV = "VISION_PROVIDER_OAUTH_EXPIRES_AT"
LEGACY_RUNTIME_AUTH_MODE_ENV = "VISION_OPENAI_AUTH_MODE"
LEGACY_RUNTIME_SHARED_API_KEY_ENV = "VISION_OPENAI_API_KEY"
LEGACY_RUNTIME_OAUTH_ACCESS_TOKEN_ENV = "VISION_OPENAI_OAUTH_ACCESS_TOKEN"
LEGACY_RUNTIME_OAUTH_ACCOUNT_ID_ENV = "VISION_OPENAI_OAUTH_ACCOUNT_ID"
LEGACY_RUNTIME_OAUTH_CLIENT_ID_ENV = "VISION_OPENAI_OAUTH_CLIENT_ID"
LEGACY_RUNTIME_OAUTH_SESSION_ID_ENV = "VISION_OPENAI_OAUTH_SESSION_ID"
LEGACY_RUNTIME_OAUTH_SCOPE_ENV = "VISION_OPENAI_OAUTH_SCOPE"
LEGACY_RUNTIME_OAUTH_EXPIRES_AT_ENV = "VISION_OPENAI_OAUTH_EXPIRES_AT"
OPTIMIZER_OCR_PROVIDER_ID_ENV = "OPTIMIZER_OCR_PROVIDER_ID"
OPTIMIZER_OCR_PROVIDER_FAMILY_ENV = "OPTIMIZER_OCR_PROVIDER_FAMILY"
OPTIMIZER_OCR_PROVIDER_BASE_URL_ENV = "OPTIMIZER_OCR_BASE_URL"
OPTIMIZER_OCR_AUTH_MODE_ENV = "OPTIMIZER_OCR_AUTH_MODE"
OPTIMIZER_OCR_API_KEY_ENV = "OPTIMIZER_OCR_API_KEY"
OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN_ENV = "OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN"
OPTIMIZER_OCR_OAUTH_ACCOUNT_ID_ENV = "OPTIMIZER_OCR_OAUTH_ACCOUNT_ID"
OPTIMIZER_OCR_MODEL_ENV = "OPTIMIZER_OCR_MODEL"
OPTIMIZER_OCR_MAX_OUTPUT_TOKENS_ENV = "OPTIMIZER_OCR_MAX_OUTPUT_TOKENS"
OPTIMIZER_OCR_TIMEOUT_SECONDS_ENV = "OPTIMIZER_OCR_TIMEOUT_SECONDS"


def oauth_logged_out_state() -> OAuthSessionState:
    return OAuthSessionState(
        status="logged_out",
        account_label="",
        status_message="No active OAuth login. OpenAI LLM runs use their stored API keys in this state.",
    )


def oauth_connected_state(
    token: OAuthTokenBundle,
    *,
    status_message: str = "OpenAI OAuth is active in the Orchestrator. OpenAI LLM modules receive only ephemeral runtime credentials.",
) -> OAuthSessionState:
    return OAuthSessionState(
        status="connected",
        account_label=_account_label(token.account_id),
        status_message=status_message,
        client_id_hint=client_id_hint(token.client_id),
        scope=token.scope,
        expires_at=token.expires_at,
        account_id=token.account_id,
        has_refresh_token=bool(token.refresh_token),
    )


def oauth_error_state(message: str, *, session_state: OAuthSessionState | None = None) -> OAuthSessionState:
    previous = session_state or OAuthSessionState()
    return OAuthSessionState(
        status="error",
        account_label=previous.account_label,
        status_message=str(message).strip(),
        client_id_hint=previous.client_id_hint,
        scope=previous.scope,
        expires_at=previous.expires_at,
        account_id=previous.account_id,
        has_refresh_token=previous.has_refresh_token,
    )


def client_id_hint(client_id: str) -> str:
    value = str(client_id or "").strip()
    if len(value) <= 8:
        return value
    return f"{value[:4]}...{value[-4:]}"


def secret_name_for_target(target: CredentialTarget) -> str:
    return SECRET_NAMES[target]


def secret_name_for_provider_target(target: CredentialTarget, provider_settings: ProviderEndpointSettings) -> str:
    provider_id = provider_settings.normalized_provider_id()
    base_url = provider_settings.normalized_base_url()
    digest = sha256(base_url.encode("utf-8")).hexdigest()[:12]
    return f"{provider_id}.{digest}.{target}.api_key"


def uses_legacy_secret_for_provider(target: CredentialTarget, provider_settings: ProviderEndpointSettings) -> bool:
    _ = target
    return (
        provider_settings.normalized_provider_id() == "openai"
        and provider_settings.normalized_base_url() == "https://api.openai.com/v1"
    )


def _account_label(account_id: str) -> str:
    value = str(account_id or "").strip()
    if not value:
        return "OpenAI OAuth"
    if len(value) <= 12:
        return f"OpenAI Account {value}"
    return f"OpenAI Account {value[:8]}...{value[-4:]}"
