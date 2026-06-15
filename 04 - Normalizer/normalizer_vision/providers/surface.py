"""Surface class for the Normalizer OpenAI provider."""
from __future__ import annotations

import logging
import time
from typing import Any

from . import transport as transport_module
from .base import sanitize_secret_text
from .payload import build_payload, message_to_input, payload_bytes, schema_supports_strict
from .policy import schema_mode
from .transport import parse_retry_after
from .workflow import generate_text_response

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """OpenAI Responses API client for the Vision Normalizer."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 300,
        transport: Any | None = None,
        provider_name: str = "openai",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or transport_module.requests
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

    @staticmethod
    def _payload_bytes(payload: dict[str, Any]) -> int | None:
        return payload_bytes(payload)

    @classmethod
    def _schema_supports_strict(cls, schema: dict[str, Any] | None) -> bool:
        _ = cls
        return schema_supports_strict(schema)

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

    def generate(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
        thinking_effort: str,
    ) -> str:
        return generate_text_response(
            self,
            messages=messages,
            schema=schema,
            max_output_tokens=max_output_tokens,
            thinking_effort=thinking_effort,
        )

    def is_available(self) -> bool:
        try:
            response = transport_module.get_models(
                self._transport,
                base_url=self.base_url,
                headers=transport_module.build_headers(self.api_key),
                timeout=10,
            )
        except Exception:
            return False
        return response.status_code == 200

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def _log_request(self, messages: list[dict[str, Any]], max_output_tokens: int, model: str) -> float:
        char_count = sum(len(str(message.get("content", ""))) for message in messages)
        roles = ",".join(str(message.get("role", "user")) for message in messages)
        logger.info(
            "[%s] -> %s | messages=%d roles=%s | ~%dk chars | max_output_tokens=%d",
            self.provider_name,
            model,
            len(messages),
            roles or "-",
            char_count // 1000,
            max_output_tokens,
        )
        return time.monotonic()

    def _log_response(self, started_at: float, model: str) -> None:
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        tokens_in = self._last_usage.get("input_tokens", self._last_usage.get("prompt_tokens", 0))
        tokens_out = self._last_usage.get("output_tokens", self._last_usage.get("completion_tokens", 0))
        logger.info(
            "[%s] <- %s | %dms | in:%d out:%d tokens | response_id=%s",
            self.provider_name,
            model,
            elapsed_ms,
            tokens_in,
            tokens_out,
            self._last_response_id or "-",
        )

    @staticmethod
    def _exception_details(exc: BaseException) -> str:
        parts: list[str] = []
        current: BaseException | None = exc
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            parts.append(sanitize_secret_text(f"{current.__class__.__name__}: {current}"))
            next_exc = current.__cause__ or current.__context__
            current = next_exc if isinstance(next_exc, BaseException) else None
        return " | caused by ".join(parts)

    @staticmethod
    def _schema_mode(schema: dict[str, Any] | None) -> str:
        return schema_mode(schema)
