from tests.providers_oauth_shared import *  # noqa: F401,F403

def test_oauth_transport_request_backend_sets_headers_and_payload(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def getcode(self) -> int:
            return 200

        def read(self) -> bytes:
            return b"event: response.completed\ndata: {\"response\":{\"id\":\"resp-1\",\"usage\":{},\"output\":[{\"content\":[{\"type\":\"output_text\",\"text\":\"{}\"}]}]}}\n\n"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("normalizer_vision.providers.oauth_transport.urllib.request.urlopen", fake_urlopen)

    status_code, raw_text = oauth_transport._request_backend(
        access_token="oauth-token",
        account_id="account-1",
        payload={"model": "gpt-5.4-mini", "stream": True},
        timeout=12,
    )

    assert status_code == 200
    assert "response.completed" in raw_text
    assert captured["url"] == oauth_transport.RESPONSES_URL
    assert captured["method"] == "POST"
    assert captured["headers"]["Authorization"] == "Bearer oauth-token"
    assert captured["headers"]["Chatgpt-account-id"] == "account-1"
    assert captured["headers"]["Accept"] == "text/event-stream"
    assert captured["body"] == {"model": "gpt-5.4-mini", "stream": True}
    assert captured["timeout"] == 12

def test_oauth_transport_http_error_returns_body(monkeypatch: pytest.MonkeyPatch):
    class FakeHttpError(urllib.error.HTTPError):
        def __init__(self):
            super().__init__(oauth_transport.RESPONSES_URL, 401, "Unauthorized", hdrs=None, fp=None)

        def read(self) -> bytes:
            return b'{"error":"unauthorized"}'

    monkeypatch.setattr(
        "normalizer_vision.providers.oauth_transport.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FakeHttpError()),
    )

    status_code, raw_text = oauth_transport._request_backend(
        access_token="oauth-token",
        account_id="account-1",
        payload={"model": "gpt-5.4-mini"},
        timeout=12,
    )

    assert status_code == 401
    assert raw_text == '{"error":"unauthorized"}'

def test_oauth_provider_redacts_backend_error_tokens(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "normalizer_vision.providers.oauth_surface.oauth_transport.run_backend_content_response",
        lambda **_kwargs: oauth_transport.TransportResult(
            success=False,
            status_code=401,
            error='Bearer oauth-secret-123 {"access_token":"oauth-secret-123"}',
        ),
    )
    provider = OAuthProvider(access_token="oauth-token", account_id="account-1", model="gpt-5.4-mini")

    with pytest.raises(ProviderError) as exc_info:
        provider.generate(
            messages=[{"role": "user", "content": "Hello"}],
            schema=None,
            max_output_tokens=15_000,
            thinking_effort="none",
        )

    message = str(exc_info.value)
    assert "oauth-secret-123" not in message
    assert "Bearer [REDACTED]" in message
