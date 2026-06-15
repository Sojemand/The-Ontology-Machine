from __future__ import annotations

from normalizer_vision.assets import load_local_profile
from normalizer_vision.prompts import get_output_schema
from normalizer_vision.providers import AnthropicProvider, GoogleProvider


def test_anthropic_provider_builds_tool_schema_payload(tmp_project_root):
    profile = load_local_profile(tmp_project_root, "housing.default.v1")
    schema = get_output_schema(profile)

    payload = AnthropicProvider.build_payload(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "system", "content": "Return JSON"}, {"role": "user", "content": "hello"}],
        schema=schema,
        max_output_tokens=1200,
        thinking_effort="none",
    )

    assert payload["tools"][0]["input_schema"] == schema
    assert payload["tool_choice"] == {"type": "tool", "name": "emit_structured_output"}
    assert payload["system"] == "Return JSON"


def test_google_provider_builds_response_json_schema_payload(tmp_project_root):
    profile = load_local_profile(tmp_project_root, "housing.default.v1")
    schema = get_output_schema(profile)

    payload = GoogleProvider.build_payload(
        model="gemini-2.5-flash",
        messages=[{"role": "system", "content": "Return JSON"}, {"role": "user", "content": "hello"}],
        schema=schema,
        max_output_tokens=1200,
        thinking_effort="none",
    )

    assert payload["generationConfig"]["responseJsonSchema"] == schema
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert payload["systemInstruction"]["parts"][0]["text"] == "Return JSON"
