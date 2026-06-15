"""Tests for retry logic and token estimation."""
from __future__ import annotations

import copy
import json
from unittest.mock import patch

import pytest

from llm_interpreter.interpreter import _call_with_backoff, _estimate_cost, estimate_tokens
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.providers import ProviderError, RateLimitError


def test_zero_retries_still_attempts_once():
    class FailingProvider:
        provider_name = "openai"

        def __init__(self):
            self.calls = 0

        def generate(self, **_kwargs):
            self.calls += 1
            raise ProviderError("boom")

    provider = FailingProvider()
    result, error_msg = _call_with_backoff(provider, [], InterpreterConfig(max_retries=0))
    assert result is None
    assert "boom" in error_msg
    assert provider.calls == 1


def test_invalid_retry_after_uses_retry_delay():
    class FlakyProvider:
        provider_name = "openai"

        def __init__(self):
            self.calls = 0

        def generate(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RateLimitError(retry_after=-3)
            return '{"ok": true}'

    with patch("llm_interpreter.interpreter.random.uniform", return_value=0), patch("llm_interpreter.interpreter.time.sleep") as mock_sleep:
        result, error_msg = _call_with_backoff(FlakyProvider(), [], InterpreterConfig(max_retries=1, retry_delay_seconds=4))
    assert result == '{"ok": true}'
    assert error_msg is None
    mock_sleep.assert_called_once_with(4)


def test_retry_after_is_honored_when_present():
    class FlakyProvider:
        provider_name = "openai"

        def __init__(self):
            self.calls = 0

        def generate(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RateLimitError(retry_after=2.5)
            return '{"ok": true}'

    with patch("llm_interpreter.interpreter.random.uniform", return_value=0), patch("llm_interpreter.interpreter.time.sleep") as mock_sleep:
        result, error_msg = _call_with_backoff(FlakyProvider(), [], InterpreterConfig(max_retries=1, retry_delay_seconds=9))
    assert result == '{"ok": true}'
    assert error_msg is None
    mock_sleep.assert_called_once_with(2.5)


def test_non_retriable_provider_error_stops_immediately():
    class FailingProvider:
        provider_name = "openai"

        def __init__(self):
            self.calls = 0

        def generate(self, **_kwargs):
            self.calls += 1
            raise ProviderError("bad request", status_code=400)

    provider = FailingProvider()
    with patch("llm_interpreter.interpreter.time.sleep") as mock_sleep:
        result, error_msg = _call_with_backoff(provider, [], InterpreterConfig(max_retries=3, retry_delay_seconds=9))
    assert result is None
    assert error_msg == "bad request"
    assert provider.calls == 1
    mock_sleep.assert_not_called()

def test_backoff_uses_prompt_schema_without_api_schema():
    class RecordingProvider:
        provider_name = "openai"

        def __init__(self):
            self.kwargs: dict[str, object] = {}

        def generate(self, **kwargs):
            self.kwargs = kwargs
            return '{"ok": true}'

    provider = RecordingProvider()
    result, error_msg = _call_with_backoff(provider, [], InterpreterConfig())
    assert result == '{"ok": true}'
    assert error_msg is None
    assert "schema" in provider.kwargs
    assert provider.kwargs["schema"] is None


def test_estimate_reports_vision_mode(sample_request_file):
    estimate = estimate_tokens(sample_request_file, InterpreterConfig())
    assert estimate["mode"] == "vision"
    assert estimate["image_count"] == 2
    assert estimate["est_total_tokens"] > estimate["est_output_tokens"]


def test_estimate_fails_without_projection_catalog(sample_request, tmp_path):
    request = copy.deepcopy(sample_request)
    request.pop("projection_catalog", None)
    request_path = tmp_path / "missing.request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")

    with pytest.raises(ProviderError, match="projection_catalog fehlt"):
        estimate_tokens(request_path, InterpreterConfig())


def test_estimate_cost_tolerates_stringly_usage():
    assert _estimate_cost("gpt-5", {"input_tokens": "1.5", "output_tokens": "2"}) is not None
    assert _estimate_cost("gpt-5", {"input_tokens": "NaN", "output_tokens": object()}) is None
