"""Shared response helpers for the normalizer contract."""
from __future__ import annotations

from ..providers import sanitize_secret_text


def error_response(message: str) -> dict:
    return {"status": "ERROR", "error": sanitize_secret_text(message)}
