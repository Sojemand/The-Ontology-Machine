"""Browser OAuth login and refresh helpers for the Orchestrator."""

from __future__ import annotations

import webbrowser
from typing import Callable
from urllib.parse import urlencode

from .oauth_callback import LoopbackCallbackServer, read_manual_callback
from .oauth_http import JsonHttpResponse, post_json
from .oauth_metadata import build_token_bundle
from .oauth_pkce import build_code_challenge, generate_code_verifier, generate_state
from .oauth_types import OAuthTokenBundle

AUTHORIZATION_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
DEFAULT_CALLBACK_PORT = 1455


def build_authorization_url(
    *,
    client_id: str,
    callback_url: str,
    scope: str,
    state: str,
    code_verifier: str,
) -> str:
    return (
        f"{AUTHORIZATION_URL}?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": callback_url,
                "scope": scope,
                "state": state,
                "code_challenge": build_code_challenge(code_verifier),
                "code_challenge_method": "S256",
                "id_token_add_organizations": "true",
                "codex_cli_simplified_flow": "true",
            }
        )
    )


def perform_oauth_login(
    *,
    client_id: str,
    scope: str,
    callback_port: int = DEFAULT_CALLBACK_PORT,
    open_browser: bool = True,
    manual_mode: bool = False,
    prompt_reader: Callable[[str], str] = input,
    printer: Callable[[str], None] = print,
    http_post: Callable[..., JsonHttpResponse] = post_json,
) -> tuple[OAuthTokenBundle, str]:
    verifier = generate_code_verifier()
    state = generate_state()
    callback_server = None
    callback_mode = "manual"
    callback_url = f"http://localhost:{callback_port}/auth/callback"
    try:
        if not manual_mode:
            callback_server = LoopbackCallbackServer(port=callback_port, expected_state=state)
            callback_server.start()
            callback_url = callback_server.callback_url
            callback_mode = "loopback"
        auth_url = build_authorization_url(
            client_id=client_id,
            callback_url=callback_url,
            scope=scope,
            state=state,
            code_verifier=verifier,
        )
        printer(f"OAuth URL:\n{auth_url}\n")
        if open_browser:
            webbrowser.open(auth_url)
        code, _ = (
            callback_server.wait_for_code(180.0)
            if callback_server is not None
            else read_manual_callback(prompt_reader, expected_state=state)
        )
    except (OSError, TimeoutError):
        auth_url = build_authorization_url(
            client_id=client_id,
            callback_url=callback_url,
            scope=scope,
            state=state,
            code_verifier=verifier,
        )
        printer(f"Loopback callback is not available. Switching to manual mode.\n{auth_url}\n")
        if open_browser:
            webbrowser.open(auth_url)
        code, _ = read_manual_callback(prompt_reader, expected_state=state)
        callback_mode = "manual_fallback"
    finally:
        if callback_server is not None:
            callback_server.close()
    response = http_post(
        TOKEN_URL,
        payload={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": callback_url,
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OAuth token exchange failed ({response.status_code}): {_error_detail(response)}")
    return _bundle_from_token_response(response, client_id_hint=client_id, scope=scope), callback_mode


def refresh_oauth_token(
    token: OAuthTokenBundle,
    *,
    http_post: Callable[..., JsonHttpResponse] = post_json,
) -> OAuthTokenBundle:
    if not token.refresh_token:
        raise RuntimeError("OAuth token cannot be refreshed without refresh_token.")
    if not token.client_id:
        raise RuntimeError("OAuth token cannot be refreshed without client_id.")
    response = http_post(
        TOKEN_URL,
        payload={
            "grant_type": "refresh_token",
            "client_id": token.client_id,
            "refresh_token": token.refresh_token,
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OAuth refresh failed ({response.status_code}): {_error_detail(response)}")
    refreshed = _bundle_from_token_response(response, client_id_hint=token.client_id, scope=token.scope)
    if refreshed.refresh_token:
        return refreshed
    return OAuthTokenBundle(
        access_token=refreshed.access_token,
        refresh_token=token.refresh_token,
        id_token=refreshed.id_token,
        token_type=refreshed.token_type,
        expires_at=refreshed.expires_at,
        account_id=refreshed.account_id,
        client_id=refreshed.client_id,
        session_id=refreshed.session_id,
        scope=refreshed.scope,
        token_status_code=refreshed.token_status_code,
    )


def _bundle_from_token_response(response: JsonHttpResponse, *, client_id_hint: str, scope: str) -> OAuthTokenBundle:
    access_token = str(response.body.get("access_token") or "")
    if not access_token:
        raise RuntimeError("OAuth token response does not contain access_token.")
    return build_token_bundle(
        access_token=access_token,
        refresh_token=str(response.body.get("refresh_token") or ""),
        id_token=str(response.body.get("id_token") or ""),
        token_type=str(response.body.get("token_type") or "Bearer"),
        scope=str(response.body.get("scope") or scope),
        status_code=response.status_code,
        fallback_client_id=client_id_hint,
    )


def _error_detail(response: JsonHttpResponse) -> str:
    return str(response.body.get("error_description") or response.body.get("error") or response.body.get("detail") or "request failed")
