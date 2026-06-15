"""OpenAI OAuth owner for the orchestrator credentials subsystem."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from . import oauth_flow, oauth_report, oauth_token_store, policy
from .oauth_types import OAuthTokenBundle
from .types import OAuthSessionState

_REFRESH_SKEW_SECONDS = 300
_SUPPORTED_REASON = "OpenAI OAuth is provided by the Orchestrator for this module."
_EMBEDDINGS_REASON = "Embeddings remain logically separate and use the separate embeddings key."


class OAuthAdapter(Protocol):
    def get_status(self) -> OAuthSessionState: ...
    def login(self) -> OAuthSessionState: ...
    def logout(self) -> OAuthSessionState: ...
    def support_for(self, module_key: str, operation: str = "") -> tuple[bool, str]: ...
    def ensure_runtime_token(self) -> OAuthTokenBundle: ...


class OrchestratorOAuthAdapter:
    def __init__(self, state_dir: Path, session_state: OAuthSessionState | None = None) -> None:
        self._state_dir = Path(state_dir)
        self._session_state = session_state or policy.oauth_logged_out_state()

    def get_status(self) -> OAuthSessionState:
        token = oauth_token_store.load_token(self._state_dir)
        if token is None:
            if self._session_state.status != "error":
                self._session_state = policy.oauth_logged_out_state()
            return self._session_state
        self._session_state = policy.oauth_connected_state(token)
        return self._session_state

    def login(self) -> OAuthSessionState:
        token, callback_mode = oauth_flow.perform_oauth_login(
            client_id=policy.OAUTH_CLIENT_ID,
            scope=policy.OAUTH_SCOPE,
            callback_port=policy.OAUTH_CALLBACK_PORT,
        )
        oauth_token_store.save_token(self._state_dir, token)
        self._session_state = policy.oauth_connected_state(
            token,
            status_message=(
                "OpenAI OAuth is active in the Orchestrator. "
                f"Login mode: {callback_mode}. LLM modules receive only ephemeral runtime credentials."
            ),
        )
        self._write_report(
            {
                "event": "login",
                "written_at": oauth_report.utc_now_iso(),
                "oauth": {
                    "client_id_hint": self._session_state.client_id_hint,
                    "callback_port": policy.OAUTH_CALLBACK_PORT,
                    "scope": self._session_state.scope,
                    "callback_mode": callback_mode,
                    "token": token.sanitized(),
                },
            }
        )
        return self._session_state

    def logout(self) -> OAuthSessionState:
        deleted = oauth_token_store.delete_token(self._state_dir)
        self._session_state = policy.oauth_logged_out_state()
        self._write_report(
            {
                "event": "logout",
                "written_at": oauth_report.utc_now_iso(),
                "oauth": {
                    "deleted_cached_token": deleted,
                    "status": self._session_state.to_dict(),
                },
            }
        )
        return self._session_state

    def support_for(self, module_key: str, operation: str = "") -> tuple[bool, str]:
        if module_key == "corpus_builder":
            return False, _EMBEDDINGS_REASON
        if module_key in policy.OAUTH_SUPPORTED_MODULES:
            return True, _SUPPORTED_REASON
        return False, "OAuth is not intended for this module in the Orchestrator."

    def ensure_runtime_token(self) -> OAuthTokenBundle:
        token = oauth_token_store.load_token(self._state_dir)
        if token is None:
            raise RuntimeError("No active OAuth login available.")
        refresh_state = "not_needed"
        if token.expires_within(_REFRESH_SKEW_SECONDS):
            try:
                token = oauth_flow.refresh_oauth_token(token)
            except Exception as exc:
                self._session_state = policy.oauth_error_state(
                    f"OAuth refresh failed: {exc}",
                    session_state=self._session_state,
                )
                self._write_report(
                    {
                        "event": "refresh_error",
                        "written_at": oauth_report.utc_now_iso(),
                        "oauth": {
                            "status": self._session_state.to_dict(),
                            "refresh": {"runtime": "failed"},
                            "error": str(exc),
                        },
                    }
                )
                raise
            oauth_token_store.save_token(self._state_dir, token)
            refresh_state = "refreshed_before_run"
        self._session_state = policy.oauth_connected_state(token)
        self._write_report(
            {
                "event": "runtime_token",
                "written_at": oauth_report.utc_now_iso(),
                "oauth": {
                    "status": self._session_state.to_dict(),
                    "refresh": {"runtime": refresh_state},
                    "token": token.sanitized(),
                },
            }
        )
        return token

    def _write_report(self, report: dict[str, object]) -> None:
        oauth_report.write_oauth_report(self._state_dir, report)


def default_oauth_adapter(state_dir: Path, session_state: OAuthSessionState | None = None) -> OAuthAdapter:
    return OrchestratorOAuthAdapter(Path(state_dir), session_state)
