from tests.providers_oauth_shared import *  # noqa: F401,F403

def test_oauth_provider_uses_json_object_for_strict_schema(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def fake_run_backend_content_response(**kwargs):
        captured.update(kwargs)
        return oauth_transport.TransportResult(success=True, status_code=200, output_text='{"ok":true}')

    monkeypatch.setattr("normalizer_vision.providers.oauth_surface.oauth_transport.run_backend_content_response", fake_run_backend_content_response)
    provider = OAuthProvider(access_token="oauth-token", account_id="account-1", model="gpt-5.4-mini")

    result = provider.generate(
        messages=[
            {"role": "system", "content": "System rule"},
            {"role": "user", "content": "Hello"},
        ],
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False},
        max_output_tokens=15_000,
        thinking_effort="none",
    )

    assert result == '{"ok":true}'
    assert captured["instructions"] == "System rule"
    assert captured["text_format"] == {"type": "json_object"}
    assert captured["content_parts"] == [{"type": "input_text", "text": "Hello"}]
    assert captured["max_output_tokens"] == 15_000
    assert captured["reasoning_effort"] == "none"

def test_oauth_provider_uses_json_object_for_soft_schema(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def fake_run_backend_content_response(**kwargs):
        captured.update(kwargs)
        return oauth_transport.TransportResult(success=True, status_code=200, output_text='{"ok":true}')

    monkeypatch.setattr("normalizer_vision.providers.oauth_surface.oauth_transport.run_backend_content_response", fake_run_backend_content_response)
    provider = OAuthProvider(access_token="oauth-token", account_id="", model="gpt-5.4-mini")

    provider.generate(
        messages=[{"role": "user", "content": "Hello"}],
        schema={"type": "object", "properties": {"ok": {"type": "string"}}},
        max_output_tokens=15_000,
        thinking_effort="none",
    )

    assert captured["text_format"] == {"type": "json_object"}
    assert "json" in str(captured["instructions"]).lower()

def test_oauth_provider_is_available_uses_json_hint(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def fake_run_backend_content_response(**kwargs):
        captured.update(kwargs)
        return oauth_transport.TransportResult(success=True, status_code=200, output_text='{"accepted":true}')

    monkeypatch.setattr("normalizer_vision.providers.oauth_surface.oauth_transport.run_backend_content_response", fake_run_backend_content_response)
    provider = OAuthProvider(access_token="oauth-token", account_id="account-1", model="gpt-5.4-mini")

    assert provider.is_available() is True
    assert "json" in str(captured["instructions"]).lower()
    assert "json" in str(captured["content_parts"][0]["text"]).lower()

def test_oauth_transport_decodes_sse_success(monkeypatch: pytest.MonkeyPatch):
    raw_text = (
        'event: response.output_text.done\n'
        'data: {"text":"{\\"ok\\":true}"}\n\n'
        'event: response.completed\n'
        'data: {"response":{"id":"resp-1","usage":{"input_tokens":5,"output_tokens":7},"output":[]}}\n\n'
    )
    monkeypatch.setattr(
        "normalizer_vision.providers.oauth_transport._request_backend",
        lambda **_kwargs: (200, raw_text),
    )

    result = oauth_transport.run_backend_content_response(
        access_token="oauth-token",
        account_id="account-1",
        model="gpt-5.4-mini",
        content_parts=[{"type": "input_text", "text": "Hello"}],
        text_format={"type": "json_object"},
        instructions="Return JSON",
        max_output_tokens=512,
        reasoning_effort="none",
        timeout=30,
    )

    assert result.success is True
    assert result.status_code == 200
    assert result.output_text == '{"ok":true}'
    assert result.response_id == "resp-1"
    assert result.usage == {"input_tokens": 5, "output_tokens": 7}
    assert result.event_count == 2

def test_oauth_transport_surfaces_sse_error(monkeypatch: pytest.MonkeyPatch):
    raw_text = 'event: error\ndata: {"message":"backend exploded"}\n\n'
    monkeypatch.setattr(
        "normalizer_vision.providers.oauth_transport._request_backend",
        lambda **_kwargs: (200, raw_text),
    )

    result = oauth_transport.run_backend_content_response(
        access_token="oauth-token",
        account_id="account-1",
        model="gpt-5.4-mini",
        content_parts=[{"type": "input_text", "text": "Hello"}],
        text_format={"type": "json_object"},
        instructions="Return JSON",
        max_output_tokens=512,
        reasoning_effort="none",
        timeout=30,
    )

    assert result.success is False
    assert result.error == "backend exploded"
    assert result.event_count == 1

def test_oauth_transport_omits_max_token_fields(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def fake_request_backend(**kwargs):
        captured.update(kwargs)
        return (
            200,
            'event: response.output_text.done\ndata: {"text":"{\\"ok\\":true}"}\n\n'
            'event: response.completed\ndata: {"response":{"id":"resp-1","usage":{},"output":[]}}\n\n',
        )

    monkeypatch.setattr(
        "normalizer_vision.providers.oauth_transport._request_backend",
        fake_request_backend,
    )

    result = oauth_transport.run_backend_content_response(
        access_token="oauth-token",
        account_id="account-1",
        model="gpt-5.4-mini",
        content_parts=[{"type": "input_text", "text": "Hello"}],
        text_format={"type": "json_object"},
        instructions="Return JSON",
        max_output_tokens=512,
        reasoning_effort="none",
        timeout=30,
    )

    assert result.success is True
    payload = captured["payload"]
    assert "max_completion_tokens" not in payload
    assert "max_output_tokens" not in payload
    assert "json" in str(payload["input"][0]["content"][0]["text"]).lower()
    assert payload["input"][0]["content"][1] == {"type": "input_text", "text": "Hello"}
