"""Surface class for the OpenAI Responses API provider."""
from __future__ import annotations

from typing import Any

from .base import LLMProvider, ProviderError, RateLimitError, sanitize_error_text
from .openai_payload import build_payload, message_to_input
from .openai_response import parse_response
from .openai_transport import parse_retry_after, request_openai


class OpenAIProvider(LLMProvider):
    """OpenAI Responses API with JSON output and high-detail images."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 300,
        provider_name: str = "openai",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._provider_name = str(provider_name or "openai").strip() or "openai"
        self._last_usage: dict[str, Any] = {}
        self._last_model: str = ""
        self._last_response_id: str = ""

    @staticmethod
    def _message_to_input(message: dict[str, Any]) -> dict[str, Any]:
        return message_to_input(message)

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        return parse_retry_after(value)

    @classmethod
    def build_payload(
        cls,
        model: str,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
        thinking_effort: str,
    ) -> dict[str, Any]:
        _ = cls
        return build_payload(model, messages, schema, max_output_tokens, thinking_effort)

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> tuple[int, dict[str, str], str]:
        return request_openai(
            base_url=self.base_url,
            api_key=self.api_key,
            method=method,
            path=path,
            payload=payload,
            timeout=timeout or self.timeout,
        )

    def generate(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
        thinking_effort: str,
    ) -> str:
        payload = self.build_payload(self.model, messages, schema, max_output_tokens, thinking_effort)
        started_at = self._log_request(messages, max_output_tokens, self.model)
        status_code, headers, response_text = self._request("POST", "/responses", payload=payload)
        if status_code == 429:
            raise RateLimitError(retry_after=self._parse_retry_after(headers.get("retry-after")))
        if status_code != 200:
            raise ProviderError(
                f"Provider API Fehler {status_code}: {sanitize_error_text(response_text)}",
                status_code=status_code,
            )
        parsed = parse_response(response_text, fallback_model=self.model)
        self._last_usage = parsed.usage
        self._last_model = parsed.model
        self._last_response_id = parsed.response_id
        self._log_response(started_at, self._last_model or self.model)
        return parsed.output_text

    def check_ready(self) -> None:
        status_code, _headers, response_text = self._request("GET", "/models", timeout=min(self.timeout, 10))
        if status_code != 200:
            raise ProviderError(
                f"Provider API Fehler {status_code}: {sanitize_error_text(response_text)}",
                status_code=status_code,
            )

    @property
    def provider_name(self) -> str:
        return self._provider_name


__all__ = ["OpenAIProvider"]
