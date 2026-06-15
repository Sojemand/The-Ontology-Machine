"""Pure credential resolution for the orchestrator credentials subsystem."""

from __future__ import annotations

from ..models import ProviderEndpointSettings, RuntimeSettingsState
from .oauth_adapter import OAuthAdapter
from .policy import CAPABILITY_SPECS, TARGET_LABELS, TARGET_ORDER
from .resolver_messages import (
    OAUTH_SOURCE,
    missing_key_message,
    oauth_block_reason,
    oauth_target_message,
    provider_display_label,
    target_message,
    target_source,
)
from .types import CredentialsState, ModuleCapability, OAuthSessionState, ResolvedCredentialProfile
from .validation import validate_credentials_state, validate_resolved_profile


def resolve_credentials_profile(
    state: CredentialsState,
    *,
    secret_presence: dict[str, bool],
    oauth_adapter: OAuthAdapter,
    runtime_settings: RuntimeSettingsState,
) -> ResolvedCredentialProfile:
    validate_credentials_state(state)
    oauth_session = oauth_adapter.get_status()
    llm_provider = runtime_settings.llm_shared_provider
    embeddings_provider = runtime_settings.embeddings_provider
    optimizer_ocr_provider = runtime_settings.optimizer_ocr_provider
    effective_auth_mode = (
        "oauth"
        if oauth_session.status == "connected" and any(
            provider.oauth_supported() for provider in (llm_provider, optimizer_ocr_provider)
        )
        else "api_keys"
    )
    target_presence = {target: bool(secret_presence.get(target, False)) for target in TARGET_ORDER}
    target_readiness: dict[str, bool] = {}
    target_sources: dict[str, str] = {}
    target_messages: dict[str, str] = {}

    for target in TARGET_ORDER:
        provider_settings = runtime_settings.provider_settings_for_target(target)
        if target == "embeddings":
            target_readiness[target] = target_presence[target] or provider_settings.api_key_is_optional()
            target_sources[target] = target_source(provider_settings, target_presence[target], target=target)
            target_messages[target] = target_message(provider_settings, target_presence[target], target=target)
            continue
        if effective_auth_mode == "api_keys" or not provider_settings.oauth_supported():
            if provider_settings.api_key_is_optional():
                target_readiness[target] = True
                target_sources[target] = target_source(provider_settings, target_presence[target], target=target)
                target_messages[target] = target_message(provider_settings, target_presence[target], target=target)
                continue
            target_readiness[target] = target_presence[target]
            target_sources[target] = target_source(provider_settings, target_presence[target], target=target)
            target_messages[target] = (
                f"{TARGET_LABELS[target]} is ready for {provider_display_label(provider_settings)} through the stored API key."
                if target_presence[target]
                else missing_key_message(provider_settings, target=target)
            )
            continue
        supported, reason = oauth_adapter.support_for(_module_key_for_target(target))
        target_readiness[target] = supported and oauth_session.status == "connected"
        target_sources[target] = OAUTH_SOURCE
        target_messages[target] = oauth_target_message(oauth_session, supported=supported, reason=reason)

    capabilities = tuple(
        _resolve_capability(
            effective_auth_mode,
            oauth_session,
            oauth_adapter,
            provider_settings,
            target_presence[target],
            module_key,
            display_name,
            target,
            operation,
        )
        for module_key, display_name, target, operation in CAPABILITY_SPECS
    )
    profile = ResolvedCredentialProfile(
        auth_mode=effective_auth_mode,
        oauth_session=oauth_session,
        target_presence=target_presence,
        target_readiness=target_readiness,
        target_sources=target_sources,
        target_messages=target_messages,
        capabilities=capabilities,
    )
    validate_resolved_profile(profile)
    return profile


def _resolve_capability(
    effective_auth_mode: str,
    oauth_session: OAuthSessionState,
    oauth_adapter: OAuthAdapter,
    provider_settings: ProviderEndpointSettings,
    has_secret: bool,
    module_key: str,
    display_name: str,
    target: str,
    operation: str,
) -> ModuleCapability:
    if target == "embeddings":
        source = target_source(provider_settings, has_secret, target=target)
        if provider_settings.api_key_is_optional():
            return _capability(module_key, display_name, operation, target, source=source)
        return _capability(
            module_key,
            display_name,
            operation,
            target,
            source=source,
            ready=has_secret,
            warning_only=not has_secret,
            block_reasons=() if has_secret else (missing_key_message(provider_settings, target=target),),
        )
    if provider_settings.api_key_is_optional():
        return _capability(
            module_key,
            display_name,
            operation,
            target,
            source=target_source(provider_settings, has_secret, target=target),
        )
    if effective_auth_mode == "api_keys" or not provider_settings.oauth_supported():
        return _capability(
            module_key,
            display_name,
            operation,
            target,
            source=target_source(provider_settings, has_secret, target=target),
            ready=has_secret,
            block_reasons=() if has_secret else (missing_key_message(provider_settings, target=target),),
        )
    supported, reason = oauth_adapter.support_for(module_key, operation)
    if not supported:
        return _capability(
            module_key,
            display_name,
            operation,
            target,
            source=OAUTH_SOURCE,
            supported=False,
            ready=False,
            block_reasons=(reason,),
        )
    if oauth_session.status == "connected":
        return _capability(module_key, display_name, operation, target, source=OAUTH_SOURCE)
    return _capability(
        module_key,
        display_name,
        operation,
        target,
        source=OAUTH_SOURCE,
        ready=False,
        block_reasons=(oauth_block_reason(oauth_session),),
    )


def _capability(
    module_key: str, display_name: str, operation: str, target: str, *, source: str,
    supported: bool = True, ready: bool = True, warning_only: bool = False,
    block_reasons: tuple[str, ...] = (),
) -> ModuleCapability:
    return ModuleCapability(
        module_key=module_key,
        display_name=display_name,
        operation=operation,
        credential_target=target,
        source=source,
        supported=supported,
        ready=ready,
        warning_only=warning_only,
        block_reasons=block_reasons,
    )


def _module_key_for_target(target: str) -> str:
    if target == "optimizer_ocr":
        return "optimizer"
    return "interpreter"
