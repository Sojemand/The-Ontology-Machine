from __future__ import annotations

from llm_interpreter.providers.oauth_surface import OAuthProvider


def test_build_backend_request_uses_json_default_instructions() -> None:
    instructions, content_parts = OAuthProvider._build_backend_request([{"role": "user", "content": "Hello"}])

    assert "json" in instructions.lower()
    assert content_parts == [{"type": "input_text", "text": "Hello"}]
