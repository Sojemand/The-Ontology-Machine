"""JWT claim parsing and token metadata derivation for Orchestrator OAuth."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any

from .oauth_types import OAuthTokenBundle

_AUTH_CLAIM = "https://api.openai.com/auth"


def build_token_bundle(
    *,
    access_token: str,
    refresh_token: str,
    id_token: str,
    token_type: str,
    scope: str,
    status_code: int,
    fallback_account_id: str = "",
    fallback_expires_at: str = "",
    fallback_client_id: str = "",
    fallback_session_id: str = "",
) -> OAuthTokenBundle:
    access_claims = decode_jwt_claims(access_token)
    id_claims = decode_jwt_claims(id_token)
    auth_claims = _claim_dict(access_claims.get(_AUTH_CLAIM)) or _claim_dict(id_claims.get(_AUTH_CLAIM)) or {}
    return OAuthTokenBundle(
        access_token=access_token,
        refresh_token=refresh_token,
        id_token=id_token,
        token_type=_normalize_token_type(token_type),
        expires_at=fallback_expires_at or _iso_from_unix(access_claims.get("exp")),
        account_id=_string_value(auth_claims.get("chatgpt_account_id")) or fallback_account_id,
        client_id=_string_value(access_claims.get("client_id")) or fallback_client_id,
        session_id=_string_value(access_claims.get("session_id")) or _string_value(id_claims.get("sid")) or fallback_session_id,
        scope=scope or _scope_string(access_claims.get("scp")),
        token_status_code=int(status_code),
    )


def decode_jwt_claims(token: str) -> dict[str, Any]:
    parts = str(token or "").split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8")
        claims = json.loads(decoded)
    except Exception:
        return {}
    return claims if isinstance(claims, dict) else {}


def _claim_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _normalize_token_type(token_type: str) -> str:
    text = str(token_type or "Bearer").strip()
    return "Bearer" if text.lower() == "bearer" else text


def _scope_string(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _string_value(value: Any) -> str:
    return str(value).strip() if value else ""


def _iso_from_unix(value: Any) -> str:
    if isinstance(value, bool):
        return ""
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(timestamp, UTC).replace(microsecond=0).isoformat()
