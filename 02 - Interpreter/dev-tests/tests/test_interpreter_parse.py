"""Tests for parsing provider JSON responses."""
from __future__ import annotations

import pytest

from llm_interpreter.interpreter import _parse_llm_response
from llm_interpreter.providers import ProviderError


def test_parses_plain_json():
    assert _parse_llm_response('{"ok": true}') == {"ok": True}


def test_parses_fenced_json():
    assert _parse_llm_response('```json\n{"ok": true}\n```') == {"ok": True}


def test_sanitizes_trailing_commas_and_decimal_commas():
    assert _parse_llm_response('{"value": 12,34,}') == {"value": 12.34}


def test_rejects_non_object_payloads():
    with pytest.raises(ProviderError, match="JSON-Parse-Fehler"):
        _parse_llm_response('["not-an-object"]')


def test_reports_truncated_json():
    truncated = '{"free_text":"' + ("x" * 220)
    with pytest.raises(ProviderError, match="abgeschnitten"):
        _parse_llm_response(truncated)


def test_sanitizes_nan_infinity_and_control_chars():
    response = '{"a": NaN, "b": Infinity, "c": -Infinity, "d": "ok\\u0001"}'
    assert _parse_llm_response(response) == {"a": None, "b": None, "c": None, "d": "ok"}
