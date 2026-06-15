from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


def response_mismatch_state(
    request_payload: Mapping[str, Any],
    response_payload: Mapping[str, Any],
    *,
    now_utc: datetime | None,
) -> str | None:
    if dict(request_payload["target_identity"]) != dict(response_payload["target_identity"]):
        return "target_identity_changed"
    if dict(request_payload["state_snapshot_identity"]) != dict(response_payload["state_snapshot_identity"]):
        return "target_identity_changed"
    expiration_policy = request_payload.get("expiration_policy")
    if isinstance(expiration_policy, Mapping):
        expires_at = expiration_policy.get("expires_at")
        if isinstance(expires_at, str):
            now = now_utc or datetime.now(timezone.utc)
            if now >= datetime.fromisoformat(expires_at.replace("Z", "+00:00")):
                return "expired_pending_interaction"
    return None
