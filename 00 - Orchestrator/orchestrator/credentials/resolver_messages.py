"""Message helpers for credential resolution."""

from __future__ import annotations

from ..models import ProviderEndpointSettings
from .policy import TARGET_LABELS
from .types import OAuthSessionState

_LLM_KEY_SOURCE = "LLM Provider API key from state/keystore.enc"
_OPTIMIZER_OCR_KEY_SOURCE = "Optimizer OCR Provider API key from state/keystore.enc"
_EMBEDDINGS_KEY_SOURCE = "Embeddings Provider API key from state/keystore.enc"
OAUTH_SOURCE = "OpenAI OAuth session from state/oauth_token.enc"


def oauth_target_message(oauth_session: OAuthSessionState, *, supported: bool, reason: str) -> str:
    if not supported:
        return reason
    if oauth_session.status == "connected":
        return oauth_session.status_message
    return oauth_block_reason(oauth_session)


def oauth_block_reason(oauth_session: OAuthSessionState) -> str:
    if oauth_session.status == "error":
        return oauth_session.status_message or "The stored OAuth session is not ready."
    return oauth_session.status_message or "No active OAuth login."


def target_source(provider_settings: ProviderEndpointSettings, has_secret: bool, *, target: str) -> str:
    provider_label = provider_display_label(provider_settings)
    if provider_settings.api_key_is_optional():
        if has_secret:
            return f"{provider_label} from state/runtime_settings.json plus API key from state/keystore.enc"
        return f"{provider_label} from state/runtime_settings.json"
    source_label = {
        "embeddings": _EMBEDDINGS_KEY_SOURCE,
        "optimizer_ocr": _OPTIMIZER_OCR_KEY_SOURCE,
    }.get(target, _LLM_KEY_SOURCE)
    return f"{source_label} for {provider_label}"


def target_message(provider_settings: ProviderEndpointSettings, has_secret: bool, *, target: str) -> str:
    label = TARGET_LABELS[target]
    provider_label = provider_display_label(provider_settings)
    if provider_settings.api_key_is_optional():
        if has_secret:
            return f"{label} is ready for {provider_label}. An optional API key is passed along when needed."
        return f"{label} is ready for {provider_label}. An API key is optional in this profile."
    return (
        f"{label} is ready for {provider_label} through the stored API key."
        if has_secret
        else missing_key_message(provider_settings, target=target)
    )


def provider_display_label(provider_settings: ProviderEndpointSettings) -> str:
    label = provider_settings.display_name()
    base_url = provider_settings.normalized_base_url()
    return f"{label} ({base_url})" if base_url else label


def missing_key_message(provider_settings: ProviderEndpointSettings, *, target: str) -> str:
    provider_label = provider_display_label(provider_settings)
    if target == "embeddings":
        return (
            f"No embeddings API key is available for {provider_label}. "
            "In this state, the Corpus Builder only skips embeddings."
        )
    if target == "optimizer_ocr":
        return (
            "No stored Optimizer OCR Provider API key is available for the configured OCR provider. "
            "Open the Orchestrator, enter and save the Optimizer OCR Provider credentials, "
            "then run the Kernel/Taxonomy workflow again."
        )
    return f"No stored LLM Provider API key is available for {provider_label}."
