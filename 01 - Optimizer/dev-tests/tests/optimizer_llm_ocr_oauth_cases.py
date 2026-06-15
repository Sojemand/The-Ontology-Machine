from __future__ import annotations

from pathlib import Path

from optimizer_ocr import workflow as llm_ocr

from optimizer_llm_ocr_support import _configure


def test_extract_page_assets_uses_interpreter_oauth_backend_shape(tmp_path: Path, monkeypatch) -> None:
    _configure(monkeypatch)
    monkeypatch.setenv("OPTIMIZER_OCR_AUTH_MODE", "oauth")
    monkeypatch.setenv("OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN", "oauth-token")
    monkeypatch.setenv("OPTIMIZER_OCR_OAUTH_ACCOUNT_ID", "account-1")
    monkeypatch.delenv("OPTIMIZER_OCR_API_KEY", raising=False)
    image_path = tmp_path / "page_001.png"
    image_path.write_bytes(b"png")
    captured: dict[str, object] = {}

    def _post_json(*_args, **_kwargs):
        raise AssertionError("OAuth optimizer_ocr must not call the platform /responses API")

    def _request_oauth_backend(**kwargs):
        captured.update(kwargs)
        raw_text = "\n".join(
            [
                "event: response.output_text.done",
                'data: {"text":"{\\"blocks\\":[{\\"id\\":\\"b1\\",\\"position\\":{\\"page\\":1},\\"value\\":\\"Hallo\\"}]}"}',
                "",
                'event: response.completed',
                'data: {"response":{"id":"resp_123","usage":{"input_tokens":12,"output_tokens":3}}}',
                "",
            ]
        )
        return 200, raw_text

    monkeypatch.setattr(llm_ocr, "_post_json", _post_json)
    monkeypatch.setattr(llm_ocr, "_request_oauth_backend", _request_oauth_backend)

    result = llm_ocr.extract_page_assets([str(image_path)], source_path=tmp_path / "scan.png")

    assert result["status"] == "success"
    assert result["blocks"][0]["value"] == "Hallo"
    assert captured["access_token"] == "oauth-token"
    assert captured["account_id"] == "account-1"
    assert captured["timeout"] == 120
    payload = captured["payload"]
    assert payload["model"] == "gpt-5.4"
    assert "max_completion_tokens" not in payload
    assert "max_output_tokens" not in payload
    assert payload["instructions"] == "Return valid json only. Return the requested payload exactly. No prose."
    assert payload["reasoning"] == {"effort": "none"}
    assert payload["stream"] is True
    assert payload["store"] is False
    assert payload["text"] == {"format": {"type": "json_object"}}
    content = payload["input"][0]["content"]
    assert content[0]["type"] == "input_text"
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")


def test_extract_page_assets_redacts_oauth_backend_errors(tmp_path: Path, monkeypatch) -> None:
    _configure(monkeypatch)
    monkeypatch.setenv("OPTIMIZER_OCR_AUTH_MODE", "oauth")
    monkeypatch.setenv("OPTIMIZER_OCR_OAUTH_ACCESS_TOKEN", "oauth-token")
    monkeypatch.delenv("OPTIMIZER_OCR_API_KEY", raising=False)
    image_path = tmp_path / "page_001.png"
    image_path.write_bytes(b"png")

    monkeypatch.setattr(
        llm_ocr,
        "_request_oauth_backend",
        lambda **_kwargs: (
            401,
            '{"access_token":"secret-token","authorization":"Bearer super-secret","detail":"OPENAI_API_KEY=sk-test"}',
        ),
    )

    result = llm_ocr.extract_page_assets([str(image_path)])

    assert result["status"] == "error"
    error = result["errors"][0]
    assert "secret-token" not in error
    assert "super-secret" not in error
    assert "sk-test" not in error
    assert "[REDACTED]" in error
