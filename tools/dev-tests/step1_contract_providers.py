from __future__ import annotations

import json
from typing import Any


class InterpreterMockProvider:
    def __init__(self, response_json: dict[str, Any]) -> None:
        self._response_text = json.dumps(response_json, ensure_ascii=False)
        self._last_usage = {"input_tokens": 1400, "output_tokens": 420}
        self._last_model = "gpt-5.4"

    def generate(self, messages, schema=None, max_output_tokens=None, thinking_effort=None) -> str:  # noqa: ANN001
        return self._response_text

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supports_vision(self) -> bool:
        return True


class NormalizerMockProvider:
    def __init__(self, response_json: dict[str, Any]) -> None:
        self._response_json = response_json

    def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:  # noqa: ANN001
        return json.dumps(self._response_json, ensure_ascii=False)

    @property
    def provider_name(self) -> str:
        return "mock"
