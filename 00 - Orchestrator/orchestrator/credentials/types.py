"""Named carriers for orchestrator credential resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AuthMode = Literal["api_keys", "oauth"]
CredentialTarget = Literal["llm_shared", "optimizer_ocr", "embeddings"]
OAuthSessionStatus = Literal["logged_out", "connected", "error"]


def _coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _coerce_auth_mode(value: Any) -> AuthMode:
    mode = _coerce_str(value, "api_keys").strip().lower()
    return "oauth" if mode == "oauth" else "api_keys"


def _coerce_oauth_status(value: Any) -> OAuthSessionStatus:
    status = _coerce_str(value, "logged_out").strip().lower()
    if status == "connected":
        return "connected"
    if status == "error":
        return "error"
    return "logged_out"


@dataclass(slots=True)
class OAuthSessionState:
    status: OAuthSessionStatus = "logged_out"
    account_label: str = ""
    status_message: str = ""
    client_id_hint: str = ""
    scope: str = ""
    expires_at: str = ""
    account_id: str = ""
    has_refresh_token: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "status": self.status,
            "account_label": self.account_label,
            "status_message": self.status_message,
            "client_id_hint": self.client_id_hint,
            "scope": self.scope,
            "expires_at": self.expires_at,
            "account_id": self.account_id,
            "has_refresh_token": self.has_refresh_token,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OAuthSessionState":
        payload = data if isinstance(data, dict) else {}
        return cls(
            status=_coerce_oauth_status(payload.get("status")),
            account_label=_coerce_str(payload.get("account_label")).strip(),
            status_message=_coerce_str(payload.get("status_message")).strip(),
            client_id_hint=_coerce_str(payload.get("client_id_hint")).strip(),
            scope=_coerce_str(payload.get("scope")).strip(),
            expires_at=_coerce_str(payload.get("expires_at")).strip(),
            account_id=_coerce_str(payload.get("account_id")).strip(),
            has_refresh_token=_coerce_bool(payload.get("has_refresh_token")),
        )


@dataclass(slots=True)
class CredentialTargetState:
    has_secret: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {"has_secret": self.has_secret}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CredentialTargetState":
        payload = data if isinstance(data, dict) else {}
        return cls(has_secret=_coerce_bool(payload.get("has_secret")))


def default_targets() -> dict[CredentialTarget, CredentialTargetState]:
    return {
        "llm_shared": CredentialTargetState(),
        "optimizer_ocr": CredentialTargetState(),
        "embeddings": CredentialTargetState(),
    }


@dataclass(slots=True)
class CredentialsState:
    auth_mode: AuthMode = "api_keys"
    targets: dict[CredentialTarget, CredentialTargetState] = field(default_factory=default_targets)
    oauth_session: OAuthSessionState = field(default_factory=OAuthSessionState)

    def to_dict(self) -> dict[str, Any]:
        return {
            "targets": {name: state.to_dict() for name, state in self.targets.items()},
            "oauth_session": self.oauth_session.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CredentialsState":
        payload = data if isinstance(data, dict) else {}
        targets = default_targets()
        raw_targets = payload.get("targets", {}) or {}
        if isinstance(raw_targets, dict):
            for name in ("llm_shared", "optimizer_ocr", "embeddings"):
                targets[name] = CredentialTargetState.from_dict(raw_targets.get(name))
        return cls(
            auth_mode=_coerce_auth_mode(payload.get("auth_mode")),
            targets=targets,
            oauth_session=OAuthSessionState.from_dict(payload.get("oauth_session")),
        )


@dataclass(frozen=True, slots=True)
class ModuleCapability:
    module_key: str
    display_name: str
    operation: str = ""
    credential_target: CredentialTarget | None = None
    source: str = ""
    supported: bool = False
    ready: bool = False
    warning_only: bool = False
    block_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolvedCredentialProfile:
    auth_mode: AuthMode
    oauth_session: OAuthSessionState
    target_presence: dict[CredentialTarget, bool]
    target_readiness: dict[CredentialTarget, bool]
    target_sources: dict[CredentialTarget, str]
    target_messages: dict[CredentialTarget, str]
    capabilities: tuple[ModuleCapability, ...]

    def capability_for(self, module_key: str, operation: str = "") -> ModuleCapability | None:
        fallback: ModuleCapability | None = None
        for capability in self.capabilities:
            if capability.module_key != module_key:
                continue
            if capability.operation == operation:
                return capability
            if capability.operation == "":
                fallback = capability
        return fallback


@dataclass(frozen=True, slots=True)
class RuntimeCredentialContext:
    module_key: str
    auth_mode: AuthMode
    operation: str = ""
    supported: bool = True
    ready: bool = False
    warning_only: bool = False
    source: str = ""
    message: str = ""
    env_overlay: dict[str, str] = field(default_factory=dict)
    block_reasons: tuple[str, ...] = ()
