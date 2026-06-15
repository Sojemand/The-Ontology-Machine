"""Base provider types for Normalizer Vision."""
from __future__ import annotations

import re

_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+"), "Bearer [REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9._\-]{6,}\b"), "sk-[REDACTED]"),
    (re.compile(r'(?i)("?(?:access_token|refresh_token|id_token|api_key|authorization)"?\s*[:=]\s*"?)([^",\s}]+)'), r"\1[REDACTED]"),
)


def sanitize_secret_text(value: object) -> str:
    text = str(value)
    for pattern, replacement in _REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class ProviderError(Exception):
    """Generic provider error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(sanitize_secret_text(message))
        self.status_code = status_code


class RateLimitError(ProviderError):
    """429 error with optional Retry-After."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
