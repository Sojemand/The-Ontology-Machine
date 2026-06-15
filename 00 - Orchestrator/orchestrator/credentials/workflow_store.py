"""Credential state and API-key store operations."""

from __future__ import annotations

from pathlib import Path

from ..models import ProviderEndpointSettings, RuntimeSettingsState
from ..state import load_runtime_settings
from . import keystore, repository
from .types import CredentialsState
from .validation import ensure_target
from .workflow_sync import sync_secret_flags


def load_credentials_state(state_dir: Path) -> CredentialsState:
    return repository.load_credentials_state(state_dir)


def save_credentials_state(state_dir: Path, state: CredentialsState) -> None:
    repository.save_credentials_state(state_dir, state)


def save_api_key(
    state_dir: Path,
    target: str,
    value: str,
    *,
    provider_settings: ProviderEndpointSettings | None = None,
) -> CredentialsState:
    ensure_target(target)
    runtime_settings = _runtime_settings_for_secret_sync(state_dir, target, provider_settings)
    keystore.save_api_key(state_dir, target, value, provider_settings=provider_settings)
    return sync_secret_flags(
        state_dir,
        repository.load_credentials_state(state_dir),
        runtime_settings=runtime_settings,
        persist=True,
    )


def load_api_key(
    state_dir: Path,
    target: str,
    *,
    provider_settings: ProviderEndpointSettings | None = None,
) -> str | None:
    ensure_target(target)
    return keystore.load_api_key(state_dir, target, provider_settings=provider_settings)


def delete_api_key(
    state_dir: Path,
    target: str,
    *,
    provider_settings: ProviderEndpointSettings | None = None,
) -> CredentialsState:
    ensure_target(target)
    runtime_settings = _runtime_settings_for_secret_sync(state_dir, target, provider_settings)
    keystore.delete_api_key(state_dir, target, provider_settings=provider_settings)
    return sync_secret_flags(
        state_dir,
        repository.load_credentials_state(state_dir),
        runtime_settings=runtime_settings,
        persist=True,
    )


def has_api_key(
    state_dir: Path,
    target: str,
    *,
    provider_settings: ProviderEndpointSettings | None = None,
) -> bool:
    ensure_target(target)
    return keystore.has_api_key(state_dir, target, provider_settings=provider_settings)


def _runtime_settings_for_secret_sync(
    state_dir: Path,
    target: str,
    provider_settings: ProviderEndpointSettings | None,
) -> RuntimeSettingsState:
    runtime_settings = load_runtime_settings(state_dir)
    if provider_settings is None:
        return runtime_settings
    payload = runtime_settings.to_dict()
    provider_key = {
        "llm_shared": "llm_shared_provider",
        "optimizer_ocr": "optimizer_ocr_provider",
        "embeddings": "embeddings_provider",
    }[target]
    payload[provider_key] = provider_settings.to_dict()
    return RuntimeSettingsState.from_dict(payload)
