"""Surface class for the Google Gemini generateContent API."""
from __future__ import annotations

import urllib.parse
from typing import Any

from .base import LLMProvider, ProviderError, RateLimitError, sanitize_error_text
from .google_payload import build_payload
from .google_response import parse_response
from .openai_transport import parse_retry_after, request_openai


class GoogleProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, *, base_url: str, timeout: int = 300, provider_name: str = "google"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._provider_name = provider_name
        self._last_usage: dict[str, Any] = {}
        self._last_model: str = ""
        self._last_response_id: str = ""

    @classmethod
    def build_payload(cls, model: str, messages: list[dict[str, Any]], schema: dict[str, Any] | None, max_output_tokens: int, thinking_effort: str) -> dict[str, Any]:
        _ = cls
        return build_payload(model, messages, schema, max_output_tokens, thinking_effort)

    def _request(self, method: str, path: str, *, payload: dict[str, Any] | None = None, timeout: int | None = None):
        return request_openai(
            base_url=self.base_url,
            api_key=None,
            method=method,
            path=path,
            payload=payload,
            timeout=timeout or self.timeout,
            query={"key": self.api_key},
        )

    def generate(self, messages: list[dict[str, Any]], schema: dict[str, Any] | None, max_output_tokens: int, thinking_effort: str) -> str:
        payload = self.build_payload(self.model, messages, schema, max_output_tokens, thinking_effort)
        model_name = urllib.parse.quote(_model_name(self.model), safe="")
        started_at = self._log_request(messages, max_output_tokens, self.model)
        status_code, headers, response_text = self._request("POST", f"/models/{model_name}:generateContent", payload=payload)
        if status_code == 429:
            raise RateLimitError(retry_after=parse_retry_after(headers.get("retry-after")))
        if status_code != 200:
            raise ProviderError(f"Provider API Fehler {status_code}: {sanitize_error_text(response_text)}", status_code=status_code)
        parsed = parse_response(response_text, fallback_model=self.model)
        self._last_usage = parsed.usage
        self._last_model = parsed.model
        self._last_response_id = parsed.response_id
        self._log_response(started_at, self._last_model or self.model)
        return parsed.output_text

    def check_ready(self) -> None:
        status_code, _headers, response_text = self._request("GET", "/models", timeout=min(self.timeout, 10))
        if status_code != 200:
            raise ProviderError(f"Provider API Fehler {status_code}: {sanitize_error_text(response_text)}", status_code=status_code)

    @property
    def provider_name(self) -> str:
        return self._provider_name


def _model_name(value: str) -> str:
    model = str(value or "").strip()
    return model[7:] if model.startswith("models/") else model
