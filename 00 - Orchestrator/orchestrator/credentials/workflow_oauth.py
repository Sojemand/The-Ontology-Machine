"""OAuth session operations for credential workflow."""

from __future__ import annotations

from pathlib import Path

from . import oauth_adapter, repository
from .types import OAuthSessionState
from .workflow_sync import sync_secret_flags, synchronized_state


def get_oauth_status(state_dir: Path) -> OAuthSessionState:
    return synchronized_state(state_dir).oauth_session


def login_with_oauth(state_dir: Path) -> OAuthSessionState:
    state = sync_secret_flags(state_dir, repository.load_credentials_state(state_dir), persist=False)
    adapter = oauth_adapter.default_oauth_adapter(state_dir, state.oauth_session)
    state.auth_mode = "oauth"
    state.oauth_session = adapter.login()
    repository.save_credentials_state(state_dir, state)
    return state.oauth_session


def logout_from_oauth(state_dir: Path) -> OAuthSessionState:
    state = sync_secret_flags(state_dir, repository.load_credentials_state(state_dir), persist=False)
    adapter = oauth_adapter.default_oauth_adapter(state_dir, state.oauth_session)
    state.auth_mode = "api_keys"
    state.oauth_session = adapter.logout()
    repository.save_credentials_state(state_dir, state)
    return state.oauth_session
