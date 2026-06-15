from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from normalizer_vision.assets import load_local_profile
from normalizer_vision.prompts import get_output_schema
from normalizer_vision.providers import OpenAIProvider, ProviderError, RateLimitError


def _ok_response(*, body: dict, request_id: str) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.headers = {"x-request-id": request_id}
    response.json.return_value = body
    response.text = str(body)
    return response


def _profile_schema(tmp_project_root):
    profile = load_local_profile(tmp_project_root, "housing.default.v1")
    return get_output_schema(profile)


@patch("normalizer_vision.providers.transport.requests.post")
def test_openai_provider_raises_on_invalid_json_when_output_hits_token_cap(mock_post, tmp_project_root):
    mock_post.return_value = _ok_response(
        request_id="req_truncated",
        body={
            "id": "resp_truncated",
            "model": "gpt-5.4-mini",
            "usage": {"input_tokens": 200, "output_tokens": 6000},
            "output_text": '{"schema_version":"1.0","processing":{"model_confidence":0.9}',
        },
    )
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini")
    with pytest.raises(ProviderError, match="ungueltiges JSON"):
        provider.generate(
            messages=[{"role": "user", "content": "hello"}],
            schema=_profile_schema(tmp_project_root),
            max_output_tokens=6000,
            thinking_effort="medium",
        )
    assert mock_post.call_count == 1
    assert mock_post.call_args.kwargs["json"]["reasoning"]["effort"] == "medium"


@patch("normalizer_vision.providers.transport.requests.post")
def test_openai_provider_falls_back_to_json_object_on_json_schema_connection_abort(mock_post, tmp_project_root):
    mock_post.side_effect = [
        requests.ConnectionError("connection aborted"),
        _ok_response(
            request_id="req_fallback",
            body={
                "id": "resp_fallback",
                "model": "gpt-5.4-mini",
                "usage": {"input_tokens": 123, "output_tokens": 45},
                "output_text": '{"ok":true}',
            },
        ),
    ]
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini")
    result = provider.generate(
        messages=[{"role": "user", "content": "hello"}],
        schema=_profile_schema(tmp_project_root),
        max_output_tokens=1000,
        thinking_effort="high",
    )
    assert result == '{"ok":true}'
    assert mock_post.call_args_list[0].kwargs["json"]["text"]["format"]["type"] == "json_schema"
    assert mock_post.call_args_list[1].kwargs["json"]["text"]["format"]["type"] == "json_object"


@patch("normalizer_vision.providers.transport.requests.post")
def test_openai_provider_falls_back_to_json_object_on_schema_rejection(mock_post, tmp_project_root):
    rejected = MagicMock()
    rejected.status_code = 400
    rejected.headers = {"x-request-id": "req_schema_bad"}
    rejected.text = "Invalid json_schema response_format: strict schema is not supported"
    mock_post.side_effect = [
        rejected,
        _ok_response(
            request_id="req_schema_fallback",
            body={
                "id": "resp_schema_fallback",
                "model": "gpt-5.4-mini",
                "usage": {"input_tokens": 123, "output_tokens": 45},
                "output_text": '{"ok":true}',
            },
        ),
    ]
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini")

    result = provider.generate(
        messages=[{"role": "user", "content": "hello"}],
        schema=_profile_schema(tmp_project_root),
        max_output_tokens=1000,
        thinking_effort="high",
    )

    assert result == '{"ok":true}'
    assert mock_post.call_args_list[0].kwargs["json"]["text"]["format"]["type"] == "json_schema"
    assert mock_post.call_args_list[1].kwargs["json"]["text"]["format"]["type"] == "json_object"


@patch("normalizer_vision.providers.transport.requests.post")
def test_openai_provider_surfaces_incomplete_output_without_token_mutation(mock_post, tmp_project_root):
    mock_post.return_value = _ok_response(
        request_id="req_cap_1",
        body={
            "id": "resp_cap_1",
            "model": "gpt-5.4-mini",
            "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
            "usage": {"input_tokens": 220, "output_tokens": 6000},
            "output_text": '{"schema_version":"1.0"',
        },
    )
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini")
    with pytest.raises(ProviderError, match="runtime_settings.max_output_tokens"):
        provider.generate(
            messages=[{"role": "user", "content": "hello"}],
            schema=_profile_schema(tmp_project_root),
            max_output_tokens=6000,
            thinking_effort="none",
        )
    assert mock_post.call_count == 1
    assert mock_post.call_args.kwargs["json"]["max_output_tokens"] == 6000


@patch("normalizer_vision.providers.transport.requests.post")
def test_openai_provider_stops_after_json_object_connection_abort(mock_post, tmp_project_root):
    conn_exc = requests.ConnectionError("connection aborted")
    mock_post.side_effect = [
        conn_exc,
        conn_exc,
    ]
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini")
    with pytest.raises(ProviderError, match="nicht erreichbar"):
        provider.generate(
            messages=[{"role": "user", "content": "hello"}],
            schema=_profile_schema(tmp_project_root),
            max_output_tokens=15000,
            thinking_effort="high",
        )
    assert mock_post.call_count == 2
    first_payload = mock_post.call_args_list[0].kwargs["json"]
    second_payload = mock_post.call_args_list[1].kwargs["json"]
    assert first_payload["text"]["format"]["type"] == "json_schema"
    assert second_payload["text"]["format"]["type"] == "json_object"
    assert second_payload["reasoning"]["effort"] == "high"
    assert second_payload["max_output_tokens"] == 15000


def test_openai_provider_raises_rate_limit_error_on_429():
    response = MagicMock()
    response.status_code = 429
    response.headers = {"retry-after": "7", "x-request-id": "req_429"}
    response.text = ""
    transport = MagicMock()
    transport.post.return_value = response
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini", transport=transport)
    with pytest.raises(RateLimitError) as exc_info:
        provider.generate([{"role": "user", "content": "hello"}], None, 1000, "none")
    assert exc_info.value.retry_after == 7.0


def test_openai_provider_raises_provider_error_on_non_200_response():
    response = MagicMock()
    response.status_code = 500
    response.headers = {"x-request-id": "req_500"}
    response.text = "internal server error"
    transport = MagicMock()
    transport.post.return_value = response
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini", transport=transport)
    with pytest.raises(ProviderError, match="500"):
        provider.generate([{"role": "user", "content": "hello"}], None, 1000, "none")


def test_openai_provider_rejects_response_without_output_text():
    response = MagicMock()
    response.status_code = 200
    response.headers = {"x-request-id": "req_empty"}
    response.text = '{"output":[]}'
    response.json.return_value = {
        "id": "resp_empty",
        "model": "gpt-5.4-mini",
        "usage": {"input_tokens": 100, "output_tokens": 10},
        "output": [],
    }
    transport = MagicMock()
    transport.post.return_value = response
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini", transport=transport)
    with pytest.raises(ProviderError, match="keinen Text-Output"):
        provider.generate([{"role": "user", "content": "hello"}], None, 1000, "none")


def test_openai_provider_redacts_tokens_in_logs(caplog: pytest.LogCaptureFixture):
    response = MagicMock()
    response.status_code = 500
    response.headers = {"x-request-id": "req_500"}
    response.text = 'Bearer oauth-secret-123 {"access_token":"oauth-secret-123","api_key":"sk-secret-987654"}'
    transport = MagicMock()
    transport.post.return_value = response
    provider = OpenAIProvider(api_key="sk-test", model="gpt-5.4-mini", transport=transport)

    with caplog.at_level(logging.WARNING, logger="normalizer_vision.providers.workflow"):
        with pytest.raises(ProviderError) as exc_info:
            provider.generate([{"role": "user", "content": "hello"}], None, 1000, "none")

    logged_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "oauth-secret-123" not in logged_text
    assert "sk-secret-987654" not in logged_text
    assert "oauth-secret-123" not in str(exc_info.value)
    assert "sk-secret-987654" not in str(exc_info.value)
