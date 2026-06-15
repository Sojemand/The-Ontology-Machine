"""Workflow stage facade for orchestrator credential actions."""

from __future__ import annotations

from .workflow_oauth import get_oauth_status, login_with_oauth, logout_from_oauth
from .workflow_runtime import resolve_credentials, resolve_runtime_credentials
from .workflow_store import (
    delete_api_key,
    has_api_key,
    load_api_key,
    load_credentials_state,
    save_api_key,
    save_credentials_state,
)

__all__ = [
    "delete_api_key",
    "get_oauth_status",
    "has_api_key",
    "load_api_key",
    "load_credentials_state",
    "login_with_oauth",
    "logout_from_oauth",
    "resolve_credentials",
    "resolve_runtime_credentials",
    "save_api_key",
    "save_credentials_state",
]
