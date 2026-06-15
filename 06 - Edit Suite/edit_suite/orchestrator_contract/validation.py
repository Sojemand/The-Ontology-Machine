"""Hard validation for the Edit Suite subprocess contract."""

from __future__ import annotations

from .types import HEALTHCHECK_ACTION


def require_action(payload: dict) -> str:
    action = payload.get("action")
    if not isinstance(action, str) or not action.strip():
        raise ValueError("action is missing or invalid.")
    if action != HEALTHCHECK_ACTION:
        raise ValueError(f"Unknown action: {action}")
    return action
