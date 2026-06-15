"""Shared provider doubles for interpreter tests."""
from __future__ import annotations

import copy
import json


class MockProvider:
    """Test double for the OpenAI provider."""

    def __init__(self, response_json: dict | None = None, response_text: str | None = None):
        self._response_text = response_text or json.dumps(response_json or {})
        self._last_usage = {"input_tokens": 1400, "output_tokens": 420}
        self._last_model = "gpt-5.4"
        self.calls: list[dict] = []

    def generate(self, messages, schema=None, max_output_tokens=None, thinking_effort=None) -> str:
        self.calls.append(
            {
                "messages": copy.deepcopy(messages),
                "schema": copy.deepcopy(schema),
                "max_output_tokens": max_output_tokens,
                "thinking_effort": thinking_effort,
            }
        )
        return self._response_text

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supports_vision(self) -> bool:
        return True
