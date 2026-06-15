"""Surface class for OpenAI-compatible Chat Completions providers."""
from __future__ import annotations

import logging

from . import transport as transport_module
from .base import ProviderError, RateLimitError, sanitize_secret_text
from .chat_payload import build_payload, message_to_chat, payload_bytes
from .chat_response import parse_response
from .transport import build_headers, parse_retry_after, request_id

logger = logging.getLogger(__name__)


class OpenAIChatProvider:
    def __init__(self, api_key: str, model: str, *, base_url: str, timeout: int = 300, transport=None, provider_name: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or transport_module.requests
        self._provider_name = provider_name
        self._last_usage: dict[str, object] = {}
        self._last_model: str = ""
        self._last_response_id: str = ""

    @staticmethod
    def _message_to_input(message: dict[str, object]) -> dict[str, object]:
        return message_to_chat(message)

    @classmethod
    def build_payload(cls, model: str, messages, schema, max_output_tokens: int, thinking_effort: str):
        _ = cls
        return build_payload(model, messages, schema, max_output_tokens, thinking_effort)

    def generate(self, messages, schema, max_output_tokens: int, thinking_effort: str) -> str:
        endpoint = f"{self.base_url}/chat/completions"
        payload = self.build_payload(self.model, messages, schema, max_output_tokens, thinking_effort)
        response = self._post_with_fallback(endpoint, payload, messages, schema, max_output_tokens, thinking_effort)
        if response.status_code == 429:
            raise RateLimitError(retry_after=parse_retry_after(response.headers.get("retry-after")))
        if response.status_code != 200:
            raise ProviderError(f"Provider API Fehler {response.status_code}: {sanitize_secret_text(response.text[:500])}", status_code=response.status_code)
        parsed = parse_response(response, fallback_model=self.model)
        if parsed.output_text and parsed.json_is_valid:
            self._last_usage = parsed.usage
            self._last_model = parsed.model
            self._last_response_id = parsed.response_id
            return parsed.output_text
        if parsed.incomplete_reason:
            raise ProviderError("Provider Chat API lieferte unvollstaendigen Output: runtime_settings.max_output_tokens muss explizit angepasst werden.")
        raise ProviderError("Provider lieferte ungueltiges JSON im Modell-Output")

    def _post_with_fallback(self, endpoint: str, payload: dict, messages, schema, max_output_tokens: int, thinking_effort: str):
        headers = build_headers(self.api_key)
        logger.info("[%s] POST %s | payload_bytes=%s", self.provider_name, endpoint, payload_bytes(payload) or "?")
        response = transport_module.post_json(self._transport, endpoint=endpoint, payload=payload, headers=headers, timeout=self.timeout)
        if response.status_code != 200 and payload.get("response_format", {}).get("type") == "json_schema":
            fallback_payload = self.build_payload(self.model, messages, None, max_output_tokens, thinking_effort)
            response = transport_module.post_json(self._transport, endpoint=endpoint, payload=fallback_payload, headers=headers, timeout=self.timeout)
        logger.info("[%s] HTTP %d von %s | request_id=%s", self.provider_name, response.status_code, endpoint, request_id(response))
        return response

    def is_available(self) -> bool:
        try:
            response = transport_module.get_models(self._transport, base_url=self.base_url, headers=build_headers(self.api_key), timeout=10)
        except Exception:
            return False
        return response.status_code == 200

    @property
    def provider_name(self) -> str:
        return self._provider_name
