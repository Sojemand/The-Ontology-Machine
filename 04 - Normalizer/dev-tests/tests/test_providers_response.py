from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from normalizer_vision.providers import ProviderError
from normalizer_vision.providers.response import parse_response


def test_parse_response_rejects_invalid_json_body():
    response = MagicMock()
    response.text = "{broken"
    response.json.side_effect = ValueError("bad json")
    with pytest.raises(ProviderError, match="ungueltiges JSON"):
        parse_response(response, fallback_model="gpt-5.4-mini")


def test_parse_response_rejects_non_object_root():
    response = MagicMock()
    response.text = '["bad"]'
    response.json.return_value = ["bad"]
    with pytest.raises(ProviderError, match="ungueltiges Antwortobjekt"):
        parse_response(response, fallback_model="gpt-5.4-mini")


def test_parse_response_reads_output_text_from_output_blocks():
    response = MagicMock()
    response.text = '{"output":[{"content":[{"type":"output_text","text":"{\\"ok\\":true}"}]}]}'
    response.json.return_value = {
        "id": "resp_fallback",
        "model": "gpt-5.4-mini",
        "usage": {"input_tokens": 123, "output_tokens": 45},
        "output": [{"content": [{"type": "output_text", "text": '{"ok":true}'}]}],
    }
    parsed = parse_response(response, fallback_model="fallback-model")
    assert parsed.output_text == '{"ok":true}'
    assert parsed.model == "gpt-5.4-mini"
    assert parsed.response_id == "resp_fallback"
    assert parsed.json_is_valid is True


def test_parse_response_tracks_incomplete_invalid_json_output():
    response = MagicMock()
    response.text = '{"status":"incomplete"}'
    response.json.return_value = {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "usage": {"output_tokens": 6000},
        "output_text": '{"schema_version":"1.0"',
    }
    parsed = parse_response(response, fallback_model="gpt-5.4-mini")
    assert parsed.output_text == '{"schema_version":"1.0"'
    assert parsed.output_tokens == 6000
    assert parsed.incomplete_reason == "max_output_tokens"
    assert parsed.json_is_valid is False
