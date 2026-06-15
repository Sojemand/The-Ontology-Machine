"""Credential state synchronization helpers."""

from __future__ import annotations

from pathlib import Path

from ..state import load_runtime_settings
from . import keystore, oauth_adapter, policy, repository
from .types import CredentialsState


def synchronized_state(state_dir: Path, *, runtime_settings=None) -> CredentialsState:
    state = sync_secret_flags(
        state_dir,
        repository.load_credentials_state(state_dir),
        runtime_settings=runtime_settings,
        persist=False,
    )
    adapter = oauth_adapter.default_oauth_adapter(state_dir, state.oauth_session)
    session = adapter.get_status()
    if state.oauth_session.to_dict() != session.to_dict():
        state.oauth_session = session
        repository.save_credentials_state(state_dir, state)
    return state


def sync_secret_flags(state_dir: Path, state: CredentialsState, *, runtime_settings=None, persist: bool = False) -> CredentialsState:
    settings = runtime_settings or load_runtime_settings(state_dir)
    changed = False
    for target in policy.TARGET_ORDER:
        has_secret = keystore.has_api_key(
            state_dir,
            target,
            provider_settings=settings.provider_settings_for_target(target),
        )
        if state.targets[target].has_secret != has_secret:
            state.targets[target].has_secret = has_secret
            changed = True
    if changed or persist:
        repository.save_credentials_state(state_dir, state)
    return state
