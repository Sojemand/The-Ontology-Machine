"""Helpers for runtime credential contexts and env overlays."""

from __future__ import annotations

from pathlib import Path

from ..models import OptimizerOcrRuntimeSettings, ProviderEndpointSettings
from . import keystore, policy
from .oauth_types import OAuthTokenBundle
from .types import ResolvedCredentialProfile, RuntimeCredentialContext


def resolve_embeddings_runtime(
    state_dir: Path,
    profile: ResolvedCredentialProfile,
    capability,
    module_key: str,
    operation: str,
    *,
    provider_settings: ProviderEndpointSettings,
) -> RuntimeCredentialContext:
    if not capability.ready:
        message = capability.block_reasons[0] if capability.block_reasons else profile.target_messages["embeddings"]
        return RuntimeCredentialContext(
            module_key=module_key,
            operation=operation,
            auth_mode=profile.auth_mode,
            supported=capability.supported,
            ready=False,
            warning_only=True,
            source=capability.source,
            message=message,
            block_reasons=capability.block_reasons,
        )
    embeddings_key = keystore.load_api_key(state_dir, "embeddings", provider_settings=provider_settings)
    if not embeddings_key and not provider_settings.api_key_is_optional():
        raise RuntimeError("Embeddings API key could not be loaded from the keystore.")
    return RuntimeCredentialContext(
        module_key=module_key,
        operation=operation,
        auth_mode=profile.auth_mode,
        supported=True,
        ready=True,
        source=capability.source,
        message=profile.target_messages["embeddings"],
        env_overlay=_provider_env_overlay(provider_settings, auth_mode="api_keys", api_key=embeddings_key),
    )


def resolve_optimizer_ocr_api_key_runtime(
    state_dir: Path,
    profile: ResolvedCredentialProfile,
    capability,
    module_key: str,
    operation: str,
    *,
    provider_settings: ProviderEndpointSettings,
    runtime_settings: OptimizerOcrRuntimeSettings,
) -> RuntimeCredentialContext:
    optimizer_key = keystore.load_api_key(state_dir, "optimizer_ocr", provider_settings=provider_settings)
    if not optimizer_key and not provider_settings.api_key_is_optional():
        raise RuntimeError("Optimizer OCR API key could not be loaded from the keystore.")
    return RuntimeCredentialContext(
        module_key=module_key,
        operation=operation,
        auth_mode="api_keys",
        supported=True,
        ready=True,
        source=capability.source,
        message=profile.target_messages["optimizer_ocr"],
        env_overlay=optimizer_ocr_env_overlay(
            provider_settings,
            runtime_settings=runtime_settings,
            auth_mode="api_keys",
            api_key=optimizer_key,
        ),
    )


def resolve_api_key_runtime(
    state_dir: Path,
    module_key: str,
    operation: str,
    source: str,
    message: str,
    *,
    provider_settings: ProviderEndpointSettings,
) -> RuntimeCredentialContext:
    llm_key = keystore.load_api_key(state_dir, "llm_shared", provider_settings=provider_settings)
    if not llm_key and not provider_settings.api_key_is_optional():
        raise RuntimeError("LLM Shared API key could not be loaded from the keystore.")
    env_overlay = _provider_env_overlay(provider_settings, auth_mode="api_keys", api_key=llm_key)
    if module_key == "normalizer":
        env_overlay["NORMALIZER_OPENAI_API_KEY"] = llm_key or ""
    return RuntimeCredentialContext(
        module_key=module_key,
        operation=operation,
        auth_mode="api_keys",
        supported=True,
        ready=True,
        source=source,
        message=message,
        env_overlay=env_overlay,
    )


def oauth_env_overlay(token: OAuthTokenBundle, *, provider_settings: ProviderEndpointSettings) -> dict[str, str]:
    overlay = _provider_env_overlay(provider_settings, auth_mode="oauth")
    overlay.update(
        {
            policy.RUNTIME_OAUTH_ACCESS_TOKEN_ENV: token.access_token,
            policy.RUNTIME_OAUTH_ACCOUNT_ID_ENV: token.account_id,
            policy.RUNTIME_OAUTH_CLIENT_ID_ENV: token.client_id,
            policy.RUNTIME_OAUTH_SESSION_ID_ENV: token.session_id,
            policy.RUNTIME_OAUTH_SCOPE_ENV: token.scope,
            policy.RUNTIME_OAUTH_EXPIRES_AT_ENV: token.expires_at,
            policy.LEGACY_RUNTIME_OAUTH_ACCESS_TOKEN_ENV: token.access_token,
            policy.LEGACY_RUNTIME_OAUTH_ACCOUNT_ID_ENV: token.account_id,
            policy.LEGACY_RUNTIME_OAUTH_CLIENT_ID_ENV: token.client_id,
            policy.LEGACY_RUNTIME_OAUTH_SESSION_ID_ENV: token.session_id,
            policy.LEGACY_RUNTIME_OAUTH_SCOPE_ENV: token.scope,
            policy.LEGACY_RUNTIME_OAUTH_EXPIRES_AT_ENV: token.expires_at,
        }
    )
    return overlay


def optimizer_ocr_oauth_env_overlay(
    token: OAuthTokenBundle,
    *,
    provider_settings: ProviderEndpointSettings,
    runtime_settings: OptimizerOcrRuntimeSettings,
) -> dict[str, str]:
    return optimizer_ocr_env_overlay(
        provider_settings,
        runtime_settings=runtime_settings,
        auth_mode="oauth",
        oauth_access_token=token.access_token,
        oauth_account_id=token.account_id,
    )


def optimizer_ocr_env_overlay(
    provider_settings: ProviderEndpointSettings,
    *,
    runtime_settings: OptimizerOcrRuntimeSettings,
    auth_mode: str,
    api_key: str | None = None,
    oauth_access_token: str | None = None,
    oauth_account_id: str | None = None,
) -> dict[str, str]:
    overlay = {
        policy.OPTIMIZER_OCR_PROVIDER_ID_ENV: provider_settings.normalized_provider_id(),
        policy.OPTIMIZER_OCR_PROVIDER_FAMILY_ENV: provider_settings.normalized_provider_family(),
        policy.OPTIMIZER_OCR_PROVIDER_BASE_URL_ENV: provider_settings.normalized_base_url(),
        policy.OPTIMIZER_OCR_AUTH_MODE_ENV: auth_mode,
        policy.OPTIMIZER_OCR_MODEL_ENV: runtime_settings.model,
        policy.OPTIMIZER_OCR_MAX_OUTPUT_TOKENS_ENV: str(runtime_settings.max_output_tokens),
        policy.OPTIMIZER_OCR_TIMEOUT_SECONDS_ENV: str(runtime_settings.timeout_seconds),
    }
    key = str(api_key or "").strip()
    if key:
        overlay[policy.OPTIMIZER_OCR_API_KEY_ENV] = key
    token = str(oauth_access_token or "").strip()
    if token:
        overlay[policy.OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN_ENV] = token
    account_id = str(oauth_account_id or "").strip()
    if account_id:
        overlay[policy.OPTIMIZER_OCR_OAUTH_ACCOUNT_ID_ENV] = account_id
    return overlay


def _provider_env_overlay(
    provider_settings: ProviderEndpointSettings,
    *,
    auth_mode: str,
    api_key: str | None = None,
) -> dict[str, str]:
    normalized_base_url = provider_settings.normalized_base_url()
    overlay = {
        policy.RUNTIME_PROVIDER_ID_ENV: provider_settings.normalized_provider_id(),
        policy.RUNTIME_PROVIDER_FAMILY_ENV: provider_settings.normalized_provider_family(),
        policy.RUNTIME_PROVIDER_BASE_URL_ENV: normalized_base_url,
        policy.RUNTIME_AUTH_MODE_ENV: auth_mode,
        policy.LEGACY_RUNTIME_AUTH_MODE_ENV: auth_mode,
        "OPENAI_API_BASE_URL": normalized_base_url,
    }
    key = str(api_key or "").strip()
    if key:
        overlay.update(
            {
                policy.RUNTIME_API_KEY_ENV: key,
                policy.LEGACY_RUNTIME_SHARED_API_KEY_ENV: key,
                "OPENAI_API_KEY": key,
            }
        )
    return overlay
