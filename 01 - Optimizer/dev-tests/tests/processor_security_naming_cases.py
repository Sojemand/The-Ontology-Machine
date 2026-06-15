from __future__ import annotations

import re

import pytest

from ingestion_layer_vision.processor import Processor

from processor_security_env import VALID_HASH


def test_build_asset_key_sanitizes_path_traversal():
    result = Processor._build_asset_key("../../etc/passwd", VALID_HASH)
    assert ".." not in result
    assert "/" not in result


def test_build_asset_key_sanitizes_null_bytes():
    result = Processor._build_asset_key("file\x00name.pdf", VALID_HASH)
    assert "\x00" not in result


def test_build_output_slug_sanitizes_shell_metacharacters():
    result = Processor._build_output_slug("; rm -rf /", f"sha256:{'b' * 64}")
    assert re.fullmatch(r"[A-Za-z0-9._-]+", result), f"Slug contains unsafe characters: {result!r}"


@pytest.mark.parametrize("value", ["", "   ", "!!!"])
def test_sanitize_output_fragment_empty_returns_fallback(value):
    result = Processor._sanitize_output_fragment(value)
    assert result, "Sanitized fragment must not be empty"
    assert re.fullmatch(r"[A-Za-z0-9._-]+", result), f"Fragment contains unsafe characters: {result!r}"
