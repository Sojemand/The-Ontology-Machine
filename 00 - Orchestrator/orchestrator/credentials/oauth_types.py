"""Named OAuth token carriers for the orchestrator credential subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True, slots=True)
class OAuthTokenBundle:
    access_token: str
    refresh_token: str
    id_token: str
    token_type: str
    expires_at: str
    account_id: str
    client_id: str
    session_id: str
    scope: str
    token_status_code: int

    def expires_within(self, seconds: int) -> bool:
        if not self.expires_at:
            return False
        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        return expires_at <= datetime.now(UTC) + timedelta(seconds=max(0, seconds))

    def sanitized(self) -> dict[str, Any]:
        return {
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "account_id": self.account_id,
            "client_id": self.client_id,
            "session_id": self.session_id,
            "scope": self.scope,
            "has_refresh_token": bool(self.refresh_token),
            "has_id_token": bool(self.id_token),
            "token_status_code": self.token_status_code,
        }
