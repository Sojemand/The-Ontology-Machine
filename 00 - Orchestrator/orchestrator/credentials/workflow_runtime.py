"""Credential profile and runtime injection resolution."""

from __future__ import annotations

from pathlib import Path

from ..state import load_runtime_settings
from . import keystore, oauth_adapter, policy, repository, resolver
from .resolver_messages import OAUTH_SOURCE
from .runtime_credentials import (
    oauth_env_overlay,
    optimizer_ocr_oauth_env_overlay,
    resolve_api_key_runtime,
    resolve_embeddings_runtime,
    resolve_optimizer_ocr_api_key_runtime,
)
from .types import ResolvedCredentialProfile, RuntimeCredentialContext
from .workflow_sync import synchronized_state


def resolve_credentials(state_dir: Path) -> ResolvedCredentialProfile:
    runtime_settings = load_runtime_settings(state_dir)
    state = synchronized_state(state_dir, runtime_settings=runtime_settings)
    adapter = oauth_adapter.default_oauth_adapter(state_dir, state.oauth_session)
    return resolver.resolve_credentials_profile(
        state,
        secret_presence=secret_presence(state_dir, runtime_settings),
        oauth_adapter=adapter,
        runtime_settings=runtime_settings,
    )


def resolve_runtime_credentials(state_dir: Path, module_key: str, operation: str = "") -> RuntimeCredentialContext:
    runtime_settings = load_runtime_settings(state_dir)
    state = synchronized_state(state_dir, runtime_settings=runtime_settings)
    adapter = oauth_adapter.default_oauth_adapter(state_dir, state.oauth_session)
    profile = resolver.resolve_credentials_profile(
        state,
        secret_presence=secret_presence(state_dir, runtime_settings),
        oauth_adapter=adapter,
        runtime_settings=runtime_settings,
    )
    capability = profile.capability_for(module_key, operation)
    if capability is None:
        return RuntimeCredentialContext(
            module_key=module_key,
            operation=operation,
            auth_mode=profile.auth_mode,
            ready=True,
            message="This module does not require credential injection by the Orchestrator.",
        )
    if capability.credential_target == "embeddings":
        return resolve_embeddings_runtime(
            state_dir,
            profile,
            capability,
            module_key,
            operation,
            provider_settings=runtime_settings.embeddings_provider,
        )
    if capability.credential_target == "optimizer_ocr":
        return resolve_optimizer_ocr_runtime(state_dir, state, adapter, profile, capability, module_key, operation, runtime_settings)
    return resolve_llm_runtime(state_dir, state, adapter, profile, capability, module_key, operation, runtime_settings)


def secret_presence(state_dir: Path, runtime_settings) -> dict[str, bool]:
    return {
        target: keystore.has_api_key(
            state_dir,
            target,
            provider_settings=runtime_settings.provider_settings_for_target(target),
        )
        for target in policy.TARGET_ORDER
    }


def blocked_runtime_context(profile, capability, module_key: str, operation: str, target: str) -> RuntimeCredentialContext:
    message = capability.block_reasons[0] if capability.block_reasons else profile.target_messages[target]
    return RuntimeCredentialContext(
        module_key=module_key,
        operation=operation,
        auth_mode=profile.auth_mode,
        supported=capability.supported,
        ready=False,
        source=capability.source,
        message=message,
        block_reasons=capability.block_reasons,
    )


def resolve_optimizer_ocr_runtime(state_dir: Path, state, adapter, profile, capability, module_key: str, operation: str, runtime_settings) -> RuntimeCredentialContext:
    if not capability.ready:
        return blocked_runtime_context(profile, capability, module_key, operation, "optimizer_ocr")
    if capability.source != OAUTH_SOURCE:
        return resolve_optimizer_ocr_api_key_runtime(
            state_dir,
            profile,
            capability,
            module_key,
            operation,
            provider_settings=runtime_settings.optimizer_ocr_provider,
            runtime_settings=runtime_settings.optimizer_ocr,
        )
    token = adapter.ensure_runtime_token()
    state.oauth_session = adapter.get_status()
    repository.save_credentials_state(state_dir, state)
    return RuntimeCredentialContext(
        module_key=module_key,
        operation=operation,
        auth_mode=profile.auth_mode,
        supported=True,
        ready=True,
        source=capability.source,
        message=profile.target_messages["optimizer_ocr"],
        env_overlay=optimizer_ocr_oauth_env_overlay(
            token,
            provider_settings=runtime_settings.optimizer_ocr_provider,
            runtime_settings=runtime_settings.optimizer_ocr,
        ),
    )


def resolve_llm_runtime(state_dir: Path, state, adapter, profile, capability, module_key: str, operation: str, runtime_settings) -> RuntimeCredentialContext:
    if not capability.ready:
        return blocked_runtime_context(profile, capability, module_key, operation, "llm_shared")
    if capability.source != OAUTH_SOURCE:
        return resolve_api_key_runtime(
            state_dir,
            module_key,
            operation,
            capability.source,
            profile.target_messages["llm_shared"],
            provider_settings=runtime_settings.llm_shared_provider,
        )
    token = adapter.ensure_runtime_token()
    state.oauth_session = adapter.get_status()
    repository.save_credentials_state(state_dir, state)
    return RuntimeCredentialContext(
        module_key=module_key,
        operation=operation,
        auth_mode=profile.auth_mode,
        supported=True,
        ready=True,
        source=capability.source,
        message=profile.target_messages["llm_shared"],
        env_overlay=oauth_env_overlay(token, provider_settings=runtime_settings.llm_shared_provider),
    )
