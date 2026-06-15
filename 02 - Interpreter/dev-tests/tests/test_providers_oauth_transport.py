from __future__ import annotations

from unittest.mock import patch

from llm_interpreter.providers import oauth_transport


def test_run_backend_content_response_uses_expected_backend_request_shape() -> None:
    captured: dict[str, object] = {}

    def _fake_request_backend(**kwargs):
        captured.update(kwargs)
        raw_text = "\n".join(
            [
                'event: response.output_text.done',
                'data: {"text":"{\\"ok\\":true}"}',
                "",
                'event: response.completed',
                'data: {"response":{"id":"resp_123","usage":{"input_tokens":12,"output_tokens":3}}}',
                "",
            ]
        )
        return 200, raw_text

    with patch("llm_interpreter.providers.oauth_transport._request_backend", side_effect=_fake_request_backend):
        result = oauth_transport.run_backend_content_response(
            access_token="token-secret",
            account_id="account-1",
            model="gpt-5.4",
            content_parts=[{"type": "input_text", "text": '{"hello":"world"}'}],
            text_format={"type": "json_object"},
            instructions="Return JSON.",
            max_output_tokens=512,
            reasoning_effort="none",
            timeout=30,
        )

    assert result.success is True
    assert result.output_text == '{"ok":true}'
    assert captured["access_token"] == "token-secret"
    assert captured["account_id"] == "account-1"
    payload = captured["payload"]
    assert payload["model"] == "gpt-5.4"
    assert "max_completion_tokens" not in payload
    assert "max_output_tokens" not in payload
    assert payload["reasoning"] == {"effort": "none"}
    assert payload["stream"] is True
    assert payload["store"] is False
    assert payload["text"] == {"format": {"type": "json_object"}}
    assert "json" in str(payload["input"][0]["content"][0]["text"]).lower()
    assert payload["input"][0]["content"][1] == {"type": "input_text", "text": '{"hello":"world"}'}


def test_run_backend_content_response_preserves_strict_schema_without_json_hint() -> None:
    captured: dict[str, object] = {}
    text_format = {
        "type": "json_schema",
        "name": "kernel_llm_output",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    }

    def _fake_request_backend(**kwargs):
        captured.update(kwargs)
        raw_text = "\n".join(
            [
                'event: response.output_text.done',
                'data: {"text":"{\\"ok\\":true}"}',
                "",
                'event: response.completed',
                'data: {"response":{"id":"resp_123","usage":{"input_tokens":12,"output_tokens":3}}}',
                "",
            ]
        )
        return 200, raw_text

    with patch("llm_interpreter.providers.oauth_transport._request_backend", side_effect=_fake_request_backend):
        result = oauth_transport.run_backend_content_response(
            access_token="token-secret",
            account_id="account-1",
            model="gpt-5.4",
            content_parts=[{"type": "input_text", "text": "produce the object"}],
            text_format=text_format,
            instructions="Return the requested payload.",
            max_output_tokens=512,
            reasoning_effort="none",
            timeout=30,
        )

    assert result.success is True
    payload = captured["payload"]
    assert payload["text"] == {"format": text_format}
    assert payload["input"][0]["content"] == [{"type": "input_text", "text": "produce the object"}]


def test_run_backend_content_response_redacts_tokens_from_http_errors() -> None:
    body = '{"access_token":"secret-token","authorization":"Bearer super-secret","detail":"OPENAI_API_KEY=sk-test"}'
    with patch("llm_interpreter.providers.oauth_transport._request_backend", return_value=(401, body)):
        result = oauth_transport.run_backend_content_response(
            access_token="token-secret",
            account_id="",
            model="gpt-5.4",
            content_parts=[{"type": "input_text", "text": '{"hello":"world"}'}],
            text_format={"type": "json_object"},
            instructions="Return JSON.",
            max_output_tokens=512,
            reasoning_effort="none",
            timeout=30,
        )

    assert result.success is False
    assert result.status_code == 401
    assert "secret-token" not in result.error
    assert "super-secret" not in result.error
    assert "sk-test" not in result.error
    assert "[REDACTED]" in result.error
