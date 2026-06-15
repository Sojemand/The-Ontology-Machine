from __future__ import annotations

from collections.abc import Mapping
from typing import Any


REDACTED = "[redacted]"
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "password",
        "raw_provider_response",
        "raw_response",
        "secret",
        "stack_trace",
        "token",
    }
)


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            if any(fragment in key_text.lower() for fragment in SENSITIVE_KEYS):
                redacted[key_text] = REDACTED
            else:
                redacted[key_text] = redact_value(child)
        return redacted
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str) and _looks_secret(value):
        return REDACTED
    return value


def safe_summary(text: object, *, limit: int = 400) -> str:
    value = str(text or "Support evidence is available in the Kernel support bundle.")
    for marker in ("Traceback", "BEGIN PRIVATE", "api_key", "Authorization:", "Bearer "):
        value = value.replace(marker, REDACTED)
    if len(value) > limit:
        value = value[: limit - 3].rstrip() + "..."
    return value


def redaction_profile() -> dict[str, Any]:
    return {
        "profile_id": "phase13_support_safe_summary.v1",
        "redacts": sorted(SENSITIVE_KEYS),
        "raw_payloads_included": False,
    }


def _looks_secret(value: str) -> bool:
    lower = value.lower()
    if "sk-" in value or "bearer " in lower:
        return True
    return False
