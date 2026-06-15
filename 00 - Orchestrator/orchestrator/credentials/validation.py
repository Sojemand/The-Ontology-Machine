"""Hard invariants for orchestrator credentials state and capability matrices."""

from __future__ import annotations

from .types import CredentialsState, ResolvedCredentialProfile

_AUTH_MODES = {"api_keys", "oauth"}
_TARGETS = {"llm_shared", "optimizer_ocr", "embeddings"}
_OAUTH_STATUSES = {"logged_out", "connected", "error"}
_CAPABILITIES = {
    ("interpreter", ""),
    ("normalizer", ""),
    ("optimizer", ""),
    ("corpus_builder", "generate_embeddings"),
}
_SERIALIZED_OAUTH_FIELDS = {
    "status",
    "account_label",
    "status_message",
    "client_id_hint",
    "scope",
    "expires_at",
    "account_id",
    "has_refresh_token",
}


def ensure_auth_mode(auth_mode: str) -> None:
    if auth_mode not in _AUTH_MODES:
        raise ValueError(f"Invalid auth mode: {auth_mode}")


def ensure_target(target: str) -> None:
    if target not in _TARGETS:
        raise ValueError(f"Invalid credential target: {target}")


def ensure_oauth_status(status: str) -> None:
    if status not in _OAUTH_STATUSES:
        raise ValueError(f"Invalid OAuth status: {status}")


def ensure_module_capability(module_key: str, operation: str = "") -> None:
    if (module_key, operation) not in _CAPABILITIES:
        raise ValueError(f"Unknown capability target: {module_key}:{operation}")


def validate_credentials_state(state: CredentialsState) -> None:
    ensure_oauth_status(state.oauth_session.status)
    for target in _TARGETS:
        ensure_target(target)
        if target not in state.targets:
            raise ValueError(f"Credential target missing from state: {target}")


def validate_serialized_state(payload: dict[str, object]) -> None:
    if set(payload) != {"targets", "oauth_session"}:
        raise ValueError("credentials_state.json has an invalid root schema")
    raw_targets = payload.get("targets")
    raw_oauth = payload.get("oauth_session")
    if not isinstance(raw_targets, dict) or set(raw_targets) != _TARGETS:
        raise ValueError("credentials_state.json has invalid target fields")
    if not isinstance(raw_oauth, dict) or set(raw_oauth) != _SERIALIZED_OAUTH_FIELDS:
        raise ValueError("credentials_state.json has invalid OAuth fields")
    for value in raw_targets.values():
        if not isinstance(value, dict) or set(value) != {"has_secret"}:
            raise ValueError("credentials_state.json stores invalid target data")


def validate_resolved_profile(profile: ResolvedCredentialProfile) -> None:
    ensure_auth_mode(profile.auth_mode)
    ensure_oauth_status(profile.oauth_session.status)
    for target in _TARGETS:
        if target not in profile.target_presence:
            raise ValueError(f"Presence metadata missing for {target}")
        if target not in profile.target_readiness:
            raise ValueError(f"Readiness metadata missing for {target}")
        if target not in profile.target_sources:
            raise ValueError(f"Source metadata missing for {target}")
        if target not in profile.target_messages:
            raise ValueError(f"Message metadata missing for {target}")
    for capability in profile.capabilities:
        ensure_module_capability(capability.module_key, capability.operation)
