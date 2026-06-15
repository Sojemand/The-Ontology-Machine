"""Surface class for the Anthropic Messages API."""
from __future__ import annotations

from . import transport as transport_module
from .anthropic_payload import build_payload
from .anthropic_response import parse_response
from .base import ProviderError, RateLimitError, sanitize_secret_text
from .transport import build_headers

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider:
    def __init__(self, api_key: str, model: str, *, base_url: str, timeout: int = 300, transport=None, provider_name: str = "anthropic"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or transport_module.requests
        self._provider_name = provider_name
        self._last_usage: dict[str, object] = {}
        self._last_model: str = ""
        self._last_response_id: str = ""

    @classmethod
    def build_payload(cls, model: str, messages, schema, max_output_tokens: int, thinking_effort: str):
        _ = cls
        return build_payload(model, messages, schema, max_output_tokens, thinking_effort)

    def generate(self, messages, schema, max_output_tokens: int, thinking_effort: str) -> str:
        response = transport_module.post_json(
            self._transport,
            endpoint=f"{self.base_url}/messages",
            payload=self.build_payload(self.model, messages, schema, max_output_tokens, thinking_effort),
            headers=build_headers(None, extra_headers={"x-api-key": self.api_key, "anthropic-version": _ANTHROPIC_VERSION}),
            timeout=self.timeout,
        )
        if response.status_code == 429:
            raise RateLimitError()
        if response.status_code != 200:
            raise ProviderError(f"Provider API Fehler {response.status_code}: {sanitize_secret_text(response.text[:500])}", status_code=response.status_code)
        parsed = parse_response(response, fallback_model=self.model)
        if parsed.output_text and parsed.json_is_valid:
            self._last_usage = parsed.usage
            self._last_model = parsed.model
            self._last_response_id = parsed.response_id
            return parsed.output_text
        if parsed.incomplete_reason:
            raise ProviderError("Provider Messages API lieferte unvollstaendigen Output: runtime_settings.max_output_tokens muss explizit angepasst werden.")
        raise ProviderError("Provider lieferte ungueltiges JSON im Modell-Output")

    def is_available(self) -> bool:
        try:
            response = self._transport.get(f"{self.base_url}/models", headers={"x-api-key": self.api_key, "anthropic-version": _ANTHROPIC_VERSION}, timeout=10)
        except Exception:
            return False
        return response.status_code == 200

    @property
    def provider_name(self) -> str:
        return self._provider_name
