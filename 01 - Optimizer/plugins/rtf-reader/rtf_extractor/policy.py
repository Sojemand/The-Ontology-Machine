"""Soft heuristics for the rtf-reader extractor."""
from __future__ import annotations


def is_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) >= 80:
        return False
    if len(stripped.split()) >= 10:
        return False
    alpha_chars = [char for char in stripped if char.isalpha()]
    return bool(alpha_chars) and all(char.isupper() for char in alpha_chars)
