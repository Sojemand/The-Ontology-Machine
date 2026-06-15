"""Request-mode helpers for profile-specific prompt variants."""
from __future__ import annotations

from typing import Any


def request_is_scan(request: dict[str, Any]) -> bool:
    source = request.get("source")
    if isinstance(source, dict) and "is_scan" in source:
        return bool(source.get("is_scan"))
    return False


__all__ = ["request_is_scan"]
