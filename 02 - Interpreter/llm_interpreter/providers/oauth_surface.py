"""Surface class for orchestrator-owned OpenAI OAuth runs."""
from __future__ import annotations

from typing import Any

from . import oauth_transport
from .base import LLMProvider, ProviderError
from .openai_payload import message_to_input, text_format_for_schema

_DEFAULT_INSTRUCTIONS = "Return valid json only. Return the requested payload exactly. No prose."
_DEFAULT_MAX_OUTPUT_TOKENS = 64
_DEFAULT_REASONING_EFFORT = "none"


class OAuthProvider(LLMProvider):
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
        started_at = self._log_request(messages, max_output_tokens, self.model)
        result = oauth_transport.run_backend_content_response(
            access_token=self.access_token,
            account_id=self.account_id,
            model=self.model,
            content_parts=content_parts,
            text_format=text_format_for_schema(schema),
            instructions=instructions,
            max_output_tokens=max_output_tokens,
            reasoning_effort=thinking_effort,
            timeout=self.timeout,
        )
        if not result.success:
            raise ProviderError(
                f"OpenAI OAuth Backend Fehler {result.status_code}: {result.error[:500]}",
                status_code=result.status_code,
            )
        self._last_usage = result.usage
        self._last_model = self.model
        self._last_response_id = result.response_id
        self._log_response(started_at, self.model)
        return result.output_text

    def check_ready(self) -> None:
        if not self.access_token:
            raise ProviderError("VISION_PROVIDER_OAUTH_ACCESS_TOKEN nicht gesetzt")
        result = oauth_transport.run_backend_content_response(
            access_token=self.access_token,
            account_id=self.account_id,
            model=self.model,
            content_parts=[{"type": "input_text", "text": 'Return this json object exactly: {"accepted":true}'}],
            text_format={"type": "json_object"},
            instructions=_DEFAULT_INSTRUCTIONS,
            max_output_tokens=_DEFAULT_MAX_OUTPUT_TOKENS,
            reasoning_effort=_DEFAULT_REASONING_EFFORT,
            timeout=min(self.timeout, 15),
        )
        if not result.success:
            raise ProviderError(
                f"OpenAI OAuth Backend Fehler {result.status_code}: {result.error[:500]}",
                status_code=result.status_code,
            )

    @property
    def provider_name(self) -> str:
        return "openai_oauth"

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


__all__ = ["OAuthProvider"]
