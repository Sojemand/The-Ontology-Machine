"""Surface class for orchestrator-owned OpenAI OAuth runs."""
from __future__ import annotations

import logging
import time
from typing import Any

from . import oauth_transport
from .base import ProviderError, sanitize_secret_text
from .payload import message_to_input

logger = logging.getLogger(__name__)
_DEFAULT_INSTRUCTIONS = "Return valid json only. Return the requested payload exactly. No prose."


class OAuthProvider:
    def __init__(self, *, access_token: str, account_id: str, model: str, timeout: int = 300):
        self.access_token = access_token
        self.account_id = account_id
        self.model = model
        self.timeout = timeout
        self._last_usage: dict[str, Any] = {}
        self._last_model: str = ""
        self._last_response_id: str = ""

    def generate(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
        thinking_effort: str,
    ) -> str:
        instructions, content_parts = self._build_backend_request(messages)
        started_at = self._log_request(messages, self.model)
        result = oauth_transport.run_backend_content_response(
            access_token=self.access_token,
            account_id=self.account_id,
            model=self.model,
            content_parts=content_parts,
            text_format=self._text_format(schema),
            instructions=instructions,
            max_output_tokens=max_output_tokens,
            reasoning_effort=thinking_effort,
            timeout=self.timeout,
        )
        if not result.success:
            raise ProviderError(
                f"OpenAI OAuth Backend Fehler {result.status_code}: {sanitize_secret_text(result.error[:500])}",
                status_code=result.status_code,
            )
        self._last_usage = result.usage
        self._last_model = self.model
        self._last_response_id = result.response_id
        self._log_response(started_at, self.model)
        return result.output_text

    def is_available(self) -> bool:
        if not self.access_token:
            return False
        try:
            result = oauth_transport.run_backend_content_response(
                access_token=self.access_token,
                account_id=self.account_id,
                model=self.model,
                content_parts=[{"type": "input_text", "text": 'Return exactly this json object: {"accepted":true}'}],
                text_format={"type": "json_object"},
                instructions=_DEFAULT_INSTRUCTIONS,
                max_output_tokens=512,
                reasoning_effort="none",
                timeout=min(self.timeout, 15),
            )
        except ProviderError:
            return False
        return result.success and result.status_code == 200

    @property
    def provider_name(self) -> str:
        return "openai_oauth"

    def _log_request(self, messages: list[dict[str, Any]], model: str) -> float:
        char_count = sum(len(str(message.get("content", ""))) for message in messages)
        roles = ",".join(str(message.get("role", "user")) for message in messages)
        logger.info(
            "[%s] -> %s | messages=%d roles=%s | ~%dk chars",
            self.provider_name,
            model,
            len(messages),
            roles or "-",
            char_count // 1000,
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
    def _build_backend_request(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        instructions: list[str] = []
        content_parts: list[dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role", "user")).strip().lower()
            content = message.get("content", "")
            if role == "system":
                if isinstance(content, str) and content.strip():
                    instructions.append(content.strip())
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text" and str(block.get("text", "")).strip():
                            instructions.append(str(block.get("text", "")).strip())
                continue
            converted = message_to_input(message)
            if role != "user":
                content_parts.append({"type": "input_text", "text": f"[{role}]"})
            for part in converted.get("content", []):
                content_parts.append(part)
        if not content_parts:
            raise ProviderError("Keine Nutzlast fuer den OpenAI OAuth Provider vorhanden")
        merged_instructions = "\n\n".join(part for part in instructions if part) or _DEFAULT_INSTRUCTIONS
        return merged_instructions, content_parts

    @staticmethod
    def _text_format(schema: dict[str, Any] | None) -> dict[str, Any]:
        del schema
        return {"type": "json_object"}


__all__ = ["OAuthProvider"]
