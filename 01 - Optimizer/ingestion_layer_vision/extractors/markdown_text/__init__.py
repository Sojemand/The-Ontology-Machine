"""Stable surface for the built-in markdown/text extractor."""
from __future__ import annotations

from .workflow import extract

__all__ = ["extract", "selftest"]


def selftest() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}
