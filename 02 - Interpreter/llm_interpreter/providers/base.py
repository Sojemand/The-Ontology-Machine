"""Base provider classes for the OpenAI-only vision interpreter."""
from __future__ import annotations

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

_REDACTION_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (
        re.compile(
            r'(?i)(["\']?(?:access_token|refresh_token|id_token|api_key|authorization)["\']?\s*[:=]\s*["\']?)([^"\'\s,}]+)'
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(
            r"(?i)\b(?:OPENAI_API_KEY|VISION_PROVIDER_API_KEY|VISION_PROVIDER_OAUTH_ACCESS_TOKEN)\s*[:=]\s*([^\s,;]+)"
        ),
        lambda match: match.group(0).split("=", 1)[0].split(":", 1)[0] + "=[REDACTED]",
    ),
    (re.compile(r"\bsk-[A-Za-z0-9_-]+\b"), "sk-[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+\b"), "[REDACTED_JWT]"),
)


def sanitize_error_text(text: str, *, limit: int = 500) -> str:
    sanitized = text or ""
    for pattern, replacement in _REDACTION_RULES:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized[:limit]


class ProviderError(Exception):
    """Generic provider error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(ProviderError):
    """429 error with optional Retry-After."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class LLMProvider:
    def check_ready(self) -> None:
        raise NotImplementedError

    def generate(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
        thinking_effort: str,
    ) -> str:
        raise NotImplementedError

    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    def supports_vision(self) -> bool:
        return True

    def _log_request(self, messages: list[dict[str, Any]], max_output_tokens: int, model: str) -> float:
        text_chars = 0
        image_count = 0
        for message in messages:
            content = message.get("content")
            if isinstance(content, str):
                text_chars += len(content)
                continue
            if not isinstance(content, list):
                continue
            for block in content:
                if block.get("type") == "text":
                    text_chars += len(block.get("text", ""))
                elif block.get("type") == "input_image":
                    image_count += 1
        logger.info(
            "[%s] -> %s | ~%dk chars | %d images | max_output_tokens=%d",
            self.provider_name, model, text_chars // 1000, image_count, max_output_tokens,
        )
        return time.monotonic()

    def _log_response(self, started_at: float, model: str) -> None:
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        usage = getattr(self, "_last_usage", {})
        tokens_in = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        tokens_out = usage.get("output_tokens", usage.get("completion_tokens", 0))
        logger.info(
            "[%s] <- %s | %dms | in:%d out:%d tokens",
            self.provider_name, model, elapsed_ms, tokens_in, tokens_out,
        )
