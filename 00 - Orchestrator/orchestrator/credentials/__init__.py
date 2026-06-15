"""Path-stable surface for orchestrator credential resolution."""

from .oauth_adapter import OAuthAdapter
from .types import (
    AuthMode,
    CredentialTarget,
    CredentialsState,
    ModuleCapability,
    OAuthSessionState,
    ResolvedCredentialProfile,
    RuntimeCredentialContext,
)
from .workflow import (
    delete_api_key,
    get_oauth_status,
    has_api_key,
    load_api_key,
    load_credentials_state,
    login_with_oauth,
    logout_from_oauth,
    resolve_credentials,
    resolve_runtime_credentials,
    save_api_key,
    save_credentials_state,
)

__all__ = [
    "AuthMode",
    "CredentialTarget",
    "CredentialsState",
    "ModuleCapability",
    "OAuthAdapter",
    "OAuthSessionState",
    "ResolvedCredentialProfile",
    "RuntimeCredentialContext",
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
